"""Hybrid retrieval pipeline: semantic (Qdrant) + BM25 → RRF ensemble → cross-encoder rerank."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from langchain_classic.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from config import settings
from retrieval.embeddings import get_embedder
from retrieval.qdrant_client import get_qdrant_client

_ARTICLE_RE = re.compile(r"(?:стаття|ст\.?)\s*(\d+)", re.IGNORECASE)

_COLLECTION_PATHS: dict[str, list[Path]] = {
    "laws": [Path("data/law/procurement_legal_dataset.jsonl")],
    "articles": [
        Path("data/infobox/articles.jsonl"),
        Path("data/infobox/comments.jsonl"),
        Path("data/infobox/courses.jsonl"),
        Path("data/infobox/faq.jsonl"),
        Path("data/infobox/news.jsonl"),
        Path("data/infobox/news_mert.jsonl"),
    ],
}


class Chunk(BaseModel):
    id: str
    doc_id: str
    text: str
    metadata: dict
    score: float


class _QdrantRetriever(BaseRetriever):
    collection: str
    filters: dict | None = None
    top_k: int = 20

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        vector = get_embedder().embed_query(query)
        qdrant_filter = None
        if self.filters:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key=k,
                        match=MatchAny(any=v)
                        if isinstance(v, list)
                        else MatchValue(value=v),
                    )
                    for k, v in self.filters.items()
                ]
            )
        response = get_qdrant_client().query_points(
            collection_name=self.collection,
            query=vector,
            limit=self.top_k,
            with_payload=True,
            query_filter=qdrant_filter,
        )
        return [
            Document(page_content=p.payload["text"], metadata=dict(p.payload))
            for p in response.points
        ]


_bm25_cache: dict[str, BM25Retriever] = {}
_reranker: CrossEncoderReranker | None = None


def _get_bm25_retriever(
    collection: str, tag_whitelist: list[str] | None = None
) -> BM25Retriever:
    cache_key = (
        f"{collection}:tags={','.join(sorted(tag_whitelist))}"
        if tag_whitelist
        else collection
    )
    if cache_key not in _bm25_cache:
        docs: list[Document] = []
        for path in _COLLECTION_PATHS.get(collection, []):
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        r = json.loads(line)
                        if tag_whitelist:
                            doc_tags = r.get("tags") or []
                            if isinstance(doc_tags, str):
                                doc_tags = [doc_tags]
                            if not any(t in tag_whitelist for t in doc_tags):
                                continue
                        docs.append(Document(page_content=r["text"], metadata=r))
        # BM25Retriever crashes on empty corpus — guard with a placeholder doc
        if not docs:
            docs = [Document(page_content="немає даних", metadata={"_placeholder": True})]
        retriever = BM25Retriever.from_documents(docs)
        retriever.k = settings.retrieval_top_k
        _bm25_cache[cache_key] = retriever
    return _bm25_cache[cache_key]


def _get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        cross_encoder = HuggingFaceCrossEncoder(model_name=settings.reranker_model)
        _reranker = CrossEncoderReranker(
            model=cross_encoder, top_n=settings.rerank_top_k
        )
    return _reranker


def _extract_article_refs(query: str) -> dict | None:
    m = _ARTICLE_RE.search(query)
    return {"article_number": m.group(1)} if m else None


def hybrid_search(
    query: str,
    collection: Literal["laws", "articles"],
    filters: dict | None = None,
    top_k: int | None = None,
) -> list[Chunk]:
    top_k = top_k if top_k is not None else settings.rerank_top_k

    if collection == "laws" and filters is None:
        filters = _extract_article_refs(query)

    # Keep Qdrant and BM25 in sync: extract tag whitelist so BM25 corpus
    # matches the same subset that Qdrant filters on.
    tag_whitelist: list[str] | None = None
    if filters and "tags" in filters:
        raw = filters["tags"]
        tag_whitelist = raw if isinstance(raw, list) else [raw]

    qdrant_ret = _QdrantRetriever(
        collection=collection,
        filters=filters,
        top_k=settings.retrieval_top_k,
    )
    bm25_ret = _get_bm25_retriever(collection, tag_whitelist=tag_whitelist)
    bm25_ret.k = settings.retrieval_top_k

    ensemble = EnsembleRetriever(
        retrievers=[qdrant_ret, bm25_ret],
        weights=[settings.hybrid_semantic_weight, settings.hybrid_bm25_weight],
    )
    pipeline = ContextualCompressionRetriever(
        base_compressor=_get_reranker(),
        base_retriever=ensemble,
    )

    docs = pipeline.invoke(query)

    return [
        Chunk(
            id=d.metadata.get("id", ""),
            doc_id=d.metadata.get("doc_id", ""),
            text=d.page_content,
            score=float(d.metadata.get("relevance_score", 0.0)),
            metadata={
                k: v
                for k, v in d.metadata.items()
                if k not in ("id", "doc_id", "text", "relevance_score")
            },
        )
        for d in docs[:top_k]
    ]
