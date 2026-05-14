#!/usr/bin/env python
"""Manual A/B comparison: semantic-only vs hybrid+rerank retrieval.

Run this after ingestion to evaluate retrieval quality:
    python scripts/ab_retrieval.py

Prints top-5 results for each query under both strategies side-by-side.
Requires Qdrant running (docker compose up -d) and ingested collections.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from retrieval.embeddings import get_embedder
from retrieval.retriever import hybrid_search
from retrieval.qdrant_client import get_qdrant_client
from config import settings

_TEST_QUERIES: list[tuple[str, str]] = [
    # (query, collection)
    ("Що таке тендерна документація?", "articles"),
    ("Стаття 17 закону про публічні закупівлі", "laws"),
    ("Як зареєструватися на майданчику Prozorro?", "articles"),
    ("Порогові значення закупівель без застосування тендеру", "laws"),
    ("Не можу завантажити файл КЕП, помилка підпису", "articles"),
    ("Умови застосування переговорної процедури", "laws"),
    ("Як подати скаргу на тендерну процедуру?", "articles"),
]

_SNIPPET_LEN = 120


def _semantic_search(query: str, collection: str, top_k: int = 5) -> list[dict]:
    vector = get_embedder().embed_query(query)
    response = get_qdrant_client().query_points(
        collection_name=collection,
        query=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "title": p.payload.get("breadcrumb") or p.payload.get("title") or p.payload.get("doc_id", ""),
            "score": round(p.score, 4),
            "text": p.payload.get("text", "")[:_SNIPPET_LEN],
        }
        for p in response.points
    ]


def _hybrid_search(query: str, collection: str, top_k: int = 5) -> list[dict]:
    chunks = hybrid_search(query, collection, top_k=top_k)  # type: ignore[arg-type]
    return [
        {
            "title": c.metadata.get("breadcrumb") or c.metadata.get("title") or c.doc_id,
            "score": round(c.score, 4),
            "text": c.text[:_SNIPPET_LEN],
        }
        for c in chunks
    ]


def _print_results(label: str, results: list[dict]) -> None:
    print(f"  [{label}]")
    if not results:
        print("    (no results)")
        return
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['score']:.4f}] {r['title']}")
        print(f"       {r['text']}...")


def main() -> None:
    print("=" * 72)
    print("A/B Retrieval Comparison: semantic-only  vs  hybrid+rerank")
    print(f"  semantic_weight={settings.hybrid_semantic_weight}  bm25_weight={settings.hybrid_bm25_weight}")
    print(f"  reranker={settings.reranker_model}  threshold={settings.rerank_score_threshold}")
    print("=" * 72)

    for query, collection in _TEST_QUERIES:
        print(f"\nQUERY ({collection}): {query}")
        print("-" * 64)
        try:
            sem_results = _semantic_search(query, collection)
        except Exception as e:
            sem_results = []
            print(f"  [semantic ERROR] {e}")
        try:
            hyb_results = _hybrid_search(query, collection)
        except Exception as e:
            hyb_results = []
            print(f"  [hybrid ERROR] {e}")

        _print_results("semantic-only", sem_results)
        print()
        _print_results("hybrid+rerank", hyb_results)
        print()

    print("=" * 72)
    print("Done. Review results above and record notes in docs/ARCHITECTURE.md § 15 if needed.")


if __name__ == "__main__":
    main()
