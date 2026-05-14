"""CLI entry point for ingestion: python -m ingest.run_ingest --collection laws|articles|all"""

import argparse

from ingest.pipeline import ingest_collection
from retrieval.qdrant_client import ensure_collections


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest JSONL datasets into Qdrant")
    parser.add_argument(
        "--collection",
        choices=["laws", "articles", "all"],
        default="all",
    )
    args = parser.parse_args()

    ensure_collections()
    targets = ["laws", "articles"] if args.collection == "all" else [args.collection]
    for col in targets:
        result = ingest_collection(col)  # type: ignore[arg-type]
        print(result)


if __name__ == "__main__":
    main()
