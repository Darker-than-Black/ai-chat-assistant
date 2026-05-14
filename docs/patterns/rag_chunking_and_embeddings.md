# RAG: chunking + embeddings

## When to use

Building or rebuilding the ingestion side of a RAG pipeline — turning source documents into vector-DB entries.

In this project: `ingest/` package handles two collections (`laws`, `articles`) with different chunking strategies. The exact chunker per collection is in `ingest/chunkers.py`.

## Minimal example

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# 1. Chunking — RecursiveCharacterTextSplitter is the workhorse
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,           # target characters per chunk
    chunk_overlap=100,        # context bleed between chunks
    separators=["\n\n", "\n", ". ", " ", ""],   # try in order; "" guarantees a split
)

# Input: a list of Documents (raw text + metadata)
docs = [
    Document(page_content="...long text...", metadata={"doc_id": "a1", "source": "Prozorro"}),
    # ...
]

chunks = splitter.split_documents(docs)
# Each chunk inherits parent metadata and gets a derived chunk_index

# 2. Embeddings — OpenAI is the default
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectors = embeddings.embed_documents([c.page_content for c in chunks])

# 3. The pair (chunk + vector) goes into Qdrant via your retriever's upsert path
```

## Pitfalls

- **`chunk_size` is in characters, not tokens.** A rough rule for English: 1 token ≈ 4 chars. For Ukrainian / Russian it's ≈ 2 chars per token (Cyrillic is more expensive in `cl100k`). Size accordingly so that `chunk_size + system_prompt + query` fits well inside the model's context.
- **Overlap matters more than people think.** Zero overlap loses cross-boundary semantics. 10-20% overlap is the standard.
- **Separator order matters.** Splitter tries `separators` in order, falling back. Putting `""` last is the safety net that guarantees no chunk exceeds `chunk_size` — but it can split mid-word.
- **Different chunking per collection.** Laws → larger chunks (article-level — keep statutes intact); articles → smaller chunks with overlap. Don't use one strategy for everything.
- **Embed in batches.** OpenAI accepts up to 2048 inputs per request. Always batch — one-by-one embedding multiplies latency and cost. `embed_documents(list)` does this internally for you.
- **Embedding text ≠ stored text.** What you embed (e.g. `breadcrumb + heading + text` for laws, `title + tags + text` for articles) can be richer than what you store and return. The embedding decides retrieval; the stored text is what reaches the LLM.
- **`text-embedding-3-large`** has higher quality but ~6× the cost and 3072 dimensions vs 1536. Default to `-small`; switch only if retrieval evals show a real gap.

## Source

`lesson-5.md` (cells 9-12 on chunking, 15-17 on embeddings/FAISS).
