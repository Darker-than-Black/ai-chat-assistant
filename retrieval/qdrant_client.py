"""Singleton Qdrant client and collection initialisation."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import settings

_VECTOR_SIZES: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        _client = QdrantClient(url=settings.qdrant_url, api_key=api_key)
    return _client


def ensure_collections() -> None:
    client = get_qdrant_client()
    size = _VECTOR_SIZES[settings.embedding_model]
    for name in (settings.qdrant_laws_collection, settings.qdrant_articles_collection):
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
