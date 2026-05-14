"""Ingestion pipeline: JSONL → embed → Qdrant upsert."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from qdrant_client.models import PointStruct

from config import settings
from ingest.chunkers import chunk_article, chunk_law
from retrieval.embeddings import get_embedder
from retrieval.qdrant_client import get_qdrant_client

_BATCH_SIZE = 100

_LAW_PATHS = [Path("data/law/procurement_legal_dataset.jsonl")]
_ARTICLE_PATHS = [
    Path("data/infobox/articles.jsonl"),
    Path("data/infobox/comments.jsonl"),
    Path("data/infobox/courses.jsonl"),
    Path("data/infobox/faq.jsonl"),
    Path("data/infobox/news.jsonl"),
    Path("data/infobox/news_mert.jsonl"),
]


def _embed_text_law(r: dict) -> str:
    return f"{r.get('breadcrumb', '')}\n{r.get('section_heading', '')}\n{r['text']}"


def _embed_text_article(r: dict) -> str:
    return f"{r['title']}\n{' '.join(r.get('tags', []))}\n{r['text']}"


def ingest_collection(collection: Literal["laws", "articles"]) -> dict:
    client = get_qdrant_client()
    embedder = get_embedder()

    if collection == "laws":
        paths = _LAW_PATHS
        chunker = chunk_law
        make_text = _embed_text_law
        col_name = settings.qdrant_laws_collection
    else:
        paths = [p for p in _ARTICLE_PATHS if p.exists()]
        chunker = chunk_article
        make_text = _embed_text_article
        col_name = settings.qdrant_articles_collection

    batch: list[tuple[str, dict]] = []
    total = 0

    def flush() -> None:
        nonlocal total
        if not batch:
            return
        texts, chunks = zip(*batch)
        vectors = embedder.embed_texts(list(texts))
        points = [
            PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_DNS, c["id"])), vector=v, payload=c)
            for c, v in zip(chunks, vectors)
        ]
        client.upsert(collection_name=col_name, points=points)
        total += len(points)
        if total % 500 == 0:
            print(f"  {col_name}: {total} chunks")
        batch.clear()

    for path in paths:
        with path.open() as f:
            for line in f:
                for chunk in chunker(json.loads(line)):
                    batch.append((make_text(chunk), chunk))
                    if len(batch) >= _BATCH_SIZE:
                        flush()
    flush()

    print(f"  {col_name}: done — {total} total")
    return {"collection": col_name, "chunks_ingested": total}
