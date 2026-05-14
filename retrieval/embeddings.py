"""OpenAI embeddings wrapper with batched encoding."""

from __future__ import annotations

import time

from langchain_openai import OpenAIEmbeddings
from openai import RateLimitError

from config import settings

_BATCH_SIZE = 100
_RETRY_DELAYS = [5, 15, 30, 60]  # seconds between retries on rate limit


class EmbeddingModel:
    def __init__(self) -> None:
        assert settings.openai_api_key, "OPENAI_API_KEY required for embeddings"
        self._model = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key.get_secret_value(),
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            for attempt, delay in enumerate([0] + _RETRY_DELAYS):
                if delay:
                    time.sleep(delay)
                try:
                    results.extend(self._model.embed_documents(batch))
                    break
                except RateLimitError:
                    if attempt == len(_RETRY_DELAYS):
                        raise
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)


_embedder: EmbeddingModel | None = None


def get_embedder() -> EmbeddingModel:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingModel()
    return _embedder
