# RAG: hybrid retrieval (semantic + BM25)

## When to use

Whenever queries can contain **specific terms** (article numbers, error codes, product names) AND **semantic intent** (paraphrased questions). Pure semantic search misses exact matches; pure BM25 misses paraphrases.

In this project: every RAG call must go through hybrid retrieval — see the "Retrieval is hybrid + reranked" invariant in `CLAUDE.md`. Particularly important for the Lawyer (statute numbers like "стаття 164-14") and Common Support (procurement-specific terminology).

## Minimal example

```python
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# Build the BM25 retriever from the same chunks loaded into the vector DB
bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 5

# Vector retriever (Qdrant, FAISS, etc.)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Ensemble — weights tunable from .env
ensemble = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6],   # BM25 / Vector
)

results = ensemble.invoke("ERROR-4532 authentication failure")
# Results merged via Reciprocal Rank Fusion (RRF) under the hood
```

## Pitfalls

- **BM25 needs the corpus in memory.** `BM25Retriever.from_documents(chunks)` loads everything into a process-local `BM25Okapi` instance. For our dataset size (laws + articles ≈ thousands of chunks) this is fine; for millions of chunks, switch to a server-side BM25 (Qdrant 1.10+ has it via sparse vectors).
- **Both retrievers should query the same chunk set.** If BM25 sees a different corpus than the vector DB, results diverge weirdly. Build BM25 from the same `Document` list that was embedded.
- **Weights are tunable** — start at `[0.4, 0.6]` and re-tune on a golden dataset. Don't optimize blind.
- **Filtering:** `EnsembleRetriever` doesn't natively forward Qdrant payload filters to BM25. For pre-filtered queries (e.g. *"only laws where `article_number == '164-14'"*), filter the corpus *before* passing it to BM25 (cache filtered subsets per common filter combination), or build BM25 only over the relevant subset.
- **Stopwords matter for non-English.** `BM25Retriever.from_documents` uses a default tokenizer. For Ukrainian, consider customizing the tokenizer (`preprocess_func` parameter on `BM25Retriever`) — naive whitespace splitting is fine for a baseline but skips morphology.
- **The ensemble output is *list of Documents*, not chunks with scores.** If you need scores for downstream reranking, call retrievers separately and merge manually, or check whether the `EnsembleRetriever` version in your `langchain-classic` exposes scores.

## Source

`lesson-5.md` (cell 24 — EnsembleRetriever with BM25 + vector).
