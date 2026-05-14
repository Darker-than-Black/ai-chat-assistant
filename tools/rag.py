"""RAG search tool for agents — all retrieval must go through this tool."""

from __future__ import annotations

from typing import cast, Literal

from langchain_core.tools import tool

from config import settings
from retrieval.retriever import hybrid_search

_MAX_CONTEXT_CHARS = 10000


def _format_chunks(chunks: list) -> str:
    blocks = []
    for chunk in chunks:
        breadcrumb = chunk.metadata.get("breadcrumb") or chunk.metadata.get(
            "title", chunk.doc_id
        )
        source = chunk.metadata.get("source_url") or chunk.doc_id
        date_str = (
            chunk.metadata.get("version_date")
            or chunk.metadata.get("date_published")
            or "невідомо"
        )
        blocks.append(
            f"---\n{breadcrumb}\n{chunk.text}\nДжерело: {source}\nДата: {date_str}"
        )

    context = "\n\n".join(blocks)
    return context[:_MAX_CONTEXT_CHARS] if len(context) > _MAX_CONTEXT_CHARS else context


@tool
def rag_search(query: str, collection: str = "laws") -> str:
    """Search the procurement knowledge base.

    Use collection='laws' for questions about Ukrainian procurement law and regulations.
    Use collection='articles' for procedural questions about Prozorro platform usage.
    Returns relevant text snippets with source citations.
    """
    chunks = hybrid_search(
        query,
        cast(Literal["laws", "articles"], collection),
        top_k=settings.rerank_top_k,
    )
    return _format_chunks(chunks)


def make_rag_search_articles(tag_whitelist: list[str] | None = None):
    filters = {"tags": tag_whitelist} if tag_whitelist else None

    @tool
    def rag_search_articles(query: str) -> str:
        """Search the internal Prozorro articles collection for procedural support answers.

        Use this tool for operational platform guidance and general procurement support that
        should come from the curated articles knowledge base. The collection is always
        'articles', and any tag restrictions are applied by the system rather than the model.
        """
        chunks = hybrid_search(
            query,
            "articles",
            filters=filters,
            top_k=settings.rerank_top_k,
        )
        return _format_chunks(chunks)

    return rag_search_articles
