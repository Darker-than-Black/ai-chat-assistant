"""Chunking strategies per collection type."""

from __future__ import annotations

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)


def chunk_law(record: dict) -> list[dict]:
    """Pass-through — law JSONL is already chunked by scripts/create_procurement_law_dataset.py."""
    return [record]


def chunk_article(record: dict) -> list[dict]:
    splits = _splitter.split_text(record["text"])
    if len(splits) <= 1:
        return [record]
    chunks = []
    for i, text in enumerate(splits):
        chunk = dict(record)
        chunk["text"] = text
        chunk["chunk_index"] = i
        chunk["id"] = hashlib.sha256(f"{record['doc_id']}-{i}".encode()).hexdigest()
        chunks.append(chunk)
    return chunks
