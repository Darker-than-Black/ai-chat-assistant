"""Ensure Qdrant collections contain data before the app starts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from ingest.pipeline import ingest_collection  # noqa: E402
from retrieval.qdrant_client import ensure_collections, get_qdrant_client  # noqa: E402

_REQUIRED_DATA_PATHS = {
    "laws": [Path("data/law/procurement_legal_dataset.jsonl")],
    "articles": [Path("data/infobox/articles.jsonl")],
}


def _point_count(collection_name: str) -> int:
    return int(
        get_qdrant_client()
        .count(collection_name=collection_name, exact=True)
        .count
    )


def _assert_data_available(collection: str) -> None:
    missing = [path for path in _REQUIRED_DATA_PATHS[collection] if not path.exists()]
    if missing:
        paths = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Cannot ingest {collection}: required data file(s) missing: {paths}. "
            "Mount ./data into the app container or run ingestion from the host checkout."
        )


def main() -> None:
    ensure_collections()
    targets = [
        ("laws", settings.qdrant_laws_collection),
        ("articles", settings.qdrant_articles_collection),
    ]
    for logical_name, collection_name in targets:
        count = _point_count(collection_name)
        if count > 0:
            print(f"{collection_name}: {count} points already indexed")
            continue
        _assert_data_available(logical_name)
        print(f"{collection_name}: empty collection, starting ingestion")
        ingest_collection(logical_name)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
