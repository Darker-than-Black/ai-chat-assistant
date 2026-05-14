# RAG: cross-encoder reranking

## When to use

After a wide-net retrieval (top-K from semantic + BM25), to filter out noise and reorder by precision. Cross-encoders score `(query, candidate)` jointly — slow but much more accurate than embedding similarity.

In this project: every RAG call ends with cross-encoder reranking via `BAAI/bge-reranker-base`. Mandatory step — see `CLAUDE.md`.

## Minimal example

```python
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Step 1: wide-net retrieval (more candidates than the final answer needs)
base_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

# Step 2: cross-encoder model — load once, keep as singleton
reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
compressor = CrossEncoderReranker(model=reranker_model, top_n=5)

# Step 3: wrap retriever — compression runs after retrieval
reranking_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever,
)

results = reranking_retriever.invoke("Що робити при помилці підпису КЕП?")
# Returns top 5 most relevant docs (after reranking the 20 candidates)
```

## Pitfalls

- **First load is slow.** The model downloads (~500MB for `bge-reranker-base`) on first use, then loads to RAM. Initialize once at app startup, not per request.
- **CPU vs GPU.** `bge-reranker-base` is fast on CPU for ≤20 candidates; for production scale move to GPU or smaller models.
- **`top_n` should be smaller than the base retriever's `k`.** If `k=20` and `top_n=5`, the reranker chooses the best 5 of 20. If `top_n >= k`, you get the original retrieval order — pointless.
- **Score thresholding** is not built into `CrossEncoderReranker`. To drop candidates below a relevance threshold, call the model directly: `reranker_model.score(pairs)` returns floats, then filter — or post-filter the result list using a wrapper.
- **Wrapping ensemble + reranker:** put ensemble as the `base_retriever`. The compressor sees ensemble's already-merged list. Order: pre-filter → semantic + BM25 (k=20 each) → ensemble → reranker (top_n=5).
- **`bge-reranker-v2-m3`** is multilingual and stronger but ~3× slower. Stick with `-base` unless evals show a clear win for our Ukrainian corpus.

## Source

`lesson-5.md` (cell 26 — `ContextualCompressionRetriever` + `CrossEncoderReranker`).
