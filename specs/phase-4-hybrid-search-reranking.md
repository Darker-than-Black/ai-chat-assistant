# Plan: Phase 4 — Hybrid Search + Reranking

## Task Description

Complete the two remaining unchecked Phase 4 items from `docs/DELIVERY_CHECKLIST.md` (§ 4.4):

1. **BM25 corpus pre-filtering** — the BM25 half of the hybrid pipeline currently ignores the `filters` dict entirely, so tag/article-number constraints only apply to the Qdrant semantic retriever. Fix `_get_bm25_retriever` to accept and apply filters at corpus load time.
2. **A/B validation script** — automate the "manual semantic-only vs hybrid+rerank on 5-10 queries" check that is listed as unchecked.

Additionally, add comprehensive retrieval unit tests to satisfy the Definition of Done (DoD requires tests before marking any checklist item complete).

Phase 4 infrastructure (BM25 index, EnsembleRetriever, CrossEncoderReranker, singleton patterns) was completed early in Phase 1 and all three sub-items in 4.1–4.3 are already checked. This plan closes the remaining gaps.

## Objective

After this plan is complete:
- `_get_bm25_retriever(collection, filters)` pre-filters the BM25 corpus so that tag-whitelist queries (Technical Support) and article-number queries (Lawyer) apply consistently to both retrieval paths (Qdrant + BM25).
- The BM25 singleton cache uses a compound key `"{collection}:{filter_json}"` to avoid filter collisions.
- An empty filtered corpus is handled gracefully instead of crashing `BM25Retriever.from_documents`.
- `hybrid_search` passes its `filters` argument to `_get_bm25_retriever` and no longer mutates the cached retriever's `k`.
- `tests/test_retriever.py` covers the full retrieval pipeline including BM25 filtering, filter matching logic, cache key logic, and score-threshold filtering.
- `scripts/validate_retrieval.py` runs 10 curated Ukrainian procurement queries in two modes (semantic-only vs full hybrid+rerank) and prints a comparison table.
- Phase 4.4 items are marked `[x]` in `DELIVERY_CHECKLIST.md`.

## Problem Statement

### Bug: BM25 corpus pre-filtering is absent

When `hybrid_search(query, "articles", filters={"tags": ["tutorial"]})` is called (as Technical Support does):

- **Qdrant path** — `_QdrantRetriever` correctly constructs a `MatchAny` filter and sends it to Qdrant. Only documents tagged `tutorial` are retrieved. ✓
- **BM25 path** — `_get_bm25_retriever("articles")` loads all 6 infobox JSONL files (~10,000 documents) into the in-memory BM25 index with no filtering. Documents with entirely unrelated tags (e.g., `"новини"`, `"коментар"`) compete with tutorial documents in the lexical ranking. ✗

This causes BM25 results to pollute the ensemble for tag-filtered queries, potentially elevating off-whitelist content before the cross-encoder reranker can demote it. For Lawyer queries containing an article reference (e.g., `{"article_number": "17"}`), the same problem exists: BM25 ranks all law chunks by term frequency rather than the specific article.

### Cache key collision risk

The current `_bm25_cache: dict[str, BM25Retriever]` uses `collection` (plain string) as key. After the fix, filtered and unfiltered BM25 retrievers for the same collection must be cached separately. Without a compound key, the first call would cache one variant and return it for all subsequent calls regardless of filters.

### Missing edge case handling

`BM25Retriever.from_documents([])` raises a `ZeroDivisionError` in `rank_bm25` when the corpus is empty. If the tag whitelist is configured but no articles match it (e.g., during development with partial data), the system crashes. The fix must handle this gracefully.

### Redundant singleton mutation

In `hybrid_search`, line `bm25_ret.k = settings.retrieval_top_k` mutates the cached `BM25Retriever` instance after retrieval from cache. `_get_bm25_retriever` already sets `k` during construction, so this line is dead code. It is thread-unsafe and creates confusion about where `k` is authoritative. It should be removed.

## Solution Approach

All changes are confined to `retrieval/retriever.py`. No agent, tool, schema, config, or graph changes are required — the fix is transparent to callers.

1. **Add `_filter_cache_key(filters) → str`** — deterministic JSON serialization of a filter dict for use as a compound cache key component.
2. **Add `_matches_bm25_filter(record, filters) → bool`** — mirrors the Qdrant filter semantics in Python: scalar values use equality, list values use set-intersection (matches `MatchAny` / `MatchValue` logic).
3. **Update `_get_bm25_retriever(collection, filters=None)`** — use compound cache key; apply `_matches_bm25_filter` when iterating JSONL; guard against empty filtered corpus.
4. **Update `hybrid_search`** — pass `filters` to `_get_bm25_retriever`; remove redundant `bm25_ret.k` mutation.
5. **Extend `tests/test_retriever.py`** — unit tests covering: filter matching logic, cache key uniqueness, BM25 pre-filtering, hybrid_search auto-filter for article refs, score-threshold behaviour, empty corpus guard.
6. **Create `scripts/validate_retrieval.py`** — standalone A/B comparison: semantic-only (Qdrant + reranker, no BM25) vs full hybrid pipeline on 10 curated queries; outputs a comparison table.

### Architecture Decisions

- **Affected graph nodes**: none — fix is purely within `retrieval/retriever.py` (called by `tools/rag.py`).
- **Schemas**: none changed.
- **RAG collection(s)**: both `laws` and `articles` benefit — article-number filter is now applied to BM25 for `laws`; tag filter is now applied to BM25 for `articles`.
- **External calls**: none.
- **Sessions / persistence**: none — BM25 cache is in-process memory only.
- **Prompt source**: none changed.

## Relevant Files

- `retrieval/retriever.py` — all changes land here: two new private helpers, updated `_get_bm25_retriever`, updated `hybrid_search`
- `tests/test_retriever.py` — extend existing 9-test file with pipeline coverage (current: `TestExtractArticleRefs` × 6, `TestChunkModel` × 3)
- `docs/DELIVERY_CHECKLIST.md` — mark Phase 4.4 remaining items `[x]` after completion

### New Files

- `scripts/validate_retrieval.py` — A/B validation: semantic-only vs hybrid+rerank on 10 curated Ukrainian procurement queries

## Implementation Phases

- [ ] **Phase 1: Core Fix** — update `retrieval/retriever.py` with pre-filtering helpers and updated pipeline
  - Status:
  - Comments:

- [ ] **Phase 2: Tests** — extend `tests/test_retriever.py` to cover the fixed pipeline
  - Status:
  - Comments:

- [ ] **Phase 3: Validation & Completion** — create `scripts/validate_retrieval.py`, run it, update checklist
  - Status:
  - Comments:

## Step by Step Tasks

### 1. Add Helper: `_filter_cache_key`

- [ ] **Add `_filter_cache_key` function** — deterministic cache key component from a filter dict. Place it immediately before `_get_bm25_retriever` in `retrieval/retriever.py`:
  ```python
  def _filter_cache_key(filters: dict | None) -> str:
      if not filters:
          return ""
      # sort_keys ensures determinism regardless of insertion order
      return json.dumps(filters, sort_keys=True, ensure_ascii=False)
  ```
  - Status:
  - Comments:

### 2. Add Helper: `_matches_bm25_filter`

- [ ] **Add `_matches_bm25_filter` function** — mirrors Qdrant's `MatchAny` / `MatchValue` semantics for in-process JSONL record filtering. Place immediately after `_filter_cache_key`:
  ```python
  def _matches_bm25_filter(record: dict, filters: dict | None) -> bool:
      """Return True if record satisfies all filter conditions.

      List filter values use set-intersection (mirrors Qdrant MatchAny).
      Scalar filter values use exact equality (mirrors Qdrant MatchValue).
      Missing record fields never match a non-None filter.
      """
      if not filters:
          return True
      for key, value in filters.items():
          record_val = record.get(key)
          if isinstance(value, list):
              if isinstance(record_val, list):
                  # Record field is also a list (e.g., tags) — need at least one overlap
                  if not any(v in record_val for v in value):
                      return False
              else:
                  # Record field is scalar — must be contained in the filter list
                  if record_val not in value:
                      return False
          else:
              # Scalar filter — exact equality
              if record_val != value:
                  return False
      return True
  ```
  - Status:
  - Comments:

### 3. Update `_get_bm25_retriever`

- [ ] **Update `_get_bm25_retriever` signature and body** — add `filters: dict | None = None` param, use compound cache key, apply `_matches_bm25_filter` per record, guard empty corpus:
  ```python
  def _get_bm25_retriever(
      collection: str, filters: dict | None = None
  ) -> BM25Retriever:
      cache_key = f"{collection}:{_filter_cache_key(filters)}"
      if cache_key not in _bm25_cache:
          docs: list[Document] = []
          for path in _COLLECTION_PATHS.get(collection, []):
              if path.exists():
                  with path.open() as f:
                      for line in f:
                          r = json.loads(line)
                          if _matches_bm25_filter(r, filters):
                              docs.append(
                                  Document(page_content=r["text"], metadata=r)
                              )
          if not docs:
              # Filtered corpus is empty (misconfigured whitelist or missing data).
              # A single empty document prevents BM25 from crashing; it returns no
              # useful results, so the Qdrant half of the ensemble carries the query.
              docs = [Document(page_content="", metadata={})]
          retriever = BM25Retriever.from_documents(docs)
          retriever.k = settings.retrieval_top_k
          _bm25_cache[cache_key] = retriever
      return _bm25_cache[cache_key]
  ```
  - Status:
  - Comments:

### 4. Update `hybrid_search`

- [ ] **Pass `filters` to `_get_bm25_retriever` and remove redundant `k` mutation** — two-line change in the body of `hybrid_search`:

  Before:
  ```python
  bm25_ret = _get_bm25_retriever(collection)
  bm25_ret.k = settings.retrieval_top_k
  ```

  After:
  ```python
  bm25_ret = _get_bm25_retriever(collection, filters)
  ```

  The `k` assignment is removed because `_get_bm25_retriever` already sets it at construction time, and mutating the cached singleton is thread-unsafe.
  - Status:
  - Comments:

### 5. Syntax Verification

- [ ] **Verify retriever module compiles cleanly**:
  ```bash
  python -m py_compile retrieval/retriever.py
  python -c "from retrieval.retriever import hybrid_search, _matches_bm25_filter, _filter_cache_key; print('OK')"
  ```
  - Status:
  - Comments:

### 6. Extend `tests/test_retriever.py` — Filter Matching Logic

- [ ] **Add `TestFilterCacheKey` test class** — verify determinism and uniqueness:
  ```python
  from retrieval.retriever import _filter_cache_key

  class TestFilterCacheKey:
      def test_none_returns_empty_string(self):
          assert _filter_cache_key(None) == ""

      def test_empty_dict_is_consistent(self):
          assert _filter_cache_key({}) == _filter_cache_key({})

      def test_different_filters_produce_different_keys(self):
          k1 = _filter_cache_key({"tags": ["tutorial"]})
          k2 = _filter_cache_key({"tags": ["news"]})
          assert k1 != k2

      def test_key_order_independent(self):
          k1 = _filter_cache_key({"a": 1, "b": 2})
          k2 = _filter_cache_key({"b": 2, "a": 1})
          assert k1 == k2

      def test_same_filter_same_key(self):
          f = {"article_number": "17"}
          assert _filter_cache_key(f) == _filter_cache_key(f)
  ```
  - Status:
  - Comments:

- [ ] **Add `TestMatchesBM25Filter` test class** — verify all filter semantics:
  ```python
  from retrieval.retriever import _matches_bm25_filter

  class TestMatchesBM25Filter:
      def test_none_filter_always_matches(self):
          assert _matches_bm25_filter({"text": "hello", "tags": ["a"]}, None) is True

      def test_scalar_filter_exact_match(self):
          assert _matches_bm25_filter({"article_number": "17"}, {"article_number": "17"}) is True

      def test_scalar_filter_no_match(self):
          assert _matches_bm25_filter({"article_number": "22"}, {"article_number": "17"}) is False

      def test_missing_field_does_not_match_scalar(self):
          assert _matches_bm25_filter({"text": "hello"}, {"article_number": "17"}) is False

      def test_list_filter_list_record_overlap(self):
          record = {"tags": ["tutorial", "реєстрація"]}
          assert _matches_bm25_filter(record, {"tags": ["tutorial", "news"]}) is True

      def test_list_filter_list_record_no_overlap(self):
          record = {"tags": ["новини"]}
          assert _matches_bm25_filter(record, {"tags": ["tutorial"]}) is False

      def test_list_filter_scalar_record_in_list(self):
          record = {"article_number": "17"}
          assert _matches_bm25_filter(record, {"article_number": ["17", "22"]}) is True

      def test_list_filter_scalar_record_not_in_list(self):
          record = {"article_number": "5"}
          assert _matches_bm25_filter(record, {"article_number": ["17", "22"]}) is False

      def test_multi_key_filter_all_must_match(self):
          record = {"article_number": "17", "type": "law"}
          assert _matches_bm25_filter(record, {"article_number": "17", "type": "law"}) is True
          assert _matches_bm25_filter(record, {"article_number": "17", "type": "article"}) is False
  ```
  - Status:
  - Comments:

### 7. Extend `tests/test_retriever.py` — BM25 Pre-filtering

- [ ] **Add `TestBM25PreFiltering` test class** — use a `tmp_path` fixture to create real JSONL files; verify corpus is filtered before indexing:
  ```python
  import json
  from pathlib import Path
  from unittest.mock import patch

  from retrieval.retriever import _get_bm25_retriever, _bm25_cache

  class TestBM25PreFiltering:
      def _write_jsonl(self, path: Path, records: list[dict]) -> None:
          path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

      def test_unfiltered_loads_all_docs(self, tmp_path, monkeypatch):
          jl = tmp_path / "test.jsonl"
          records = [
              {"text": "tutorial text", "tags": ["tutorial"], "id": "1", "doc_id": "1"},
              {"text": "news text", "tags": ["новини"], "id": "2", "doc_id": "2"},
          ]
          self._write_jsonl(jl, records)
          paths = {"test_col": [jl]}
          cache: dict = {}
          with patch("retrieval.retriever._COLLECTION_PATHS", paths), \
               patch("retrieval.retriever._bm25_cache", cache):
              ret = _get_bm25_retriever("test_col")
              # BM25Retriever stores docs in its corpus
              assert len(ret.docs) == 2

      def test_filtered_loads_only_matching_docs(self, tmp_path, monkeypatch):
          jl = tmp_path / "test.jsonl"
          records = [
              {"text": "tutorial text", "tags": ["tutorial"], "id": "1", "doc_id": "1"},
              {"text": "news text", "tags": ["новини"], "id": "2", "doc_id": "2"},
              {"text": "another tutorial", "tags": ["tutorial", "extra"], "id": "3", "doc_id": "3"},
          ]
          self._write_jsonl(jl, records)
          paths = {"test_col": [jl]}
          cache: dict = {}
          with patch("retrieval.retriever._COLLECTION_PATHS", paths), \
               patch("retrieval.retriever._bm25_cache", cache):
              ret = _get_bm25_retriever("test_col", {"tags": ["tutorial"]})
              assert len(ret.docs) == 2

      def test_filtered_and_unfiltered_are_separate_cache_entries(self, tmp_path):
          jl = tmp_path / "test.jsonl"
          records = [
              {"text": "tutorial", "tags": ["tutorial"], "id": "1", "doc_id": "1"},
              {"text": "news", "tags": ["новини"], "id": "2", "doc_id": "2"},
          ]
          self._write_jsonl(jl, records)
          paths = {"test_col": [jl]}
          cache: dict = {}
          with patch("retrieval.retriever._COLLECTION_PATHS", paths), \
               patch("retrieval.retriever._bm25_cache", cache):
              _get_bm25_retriever("test_col")
              _get_bm25_retriever("test_col", {"tags": ["tutorial"]})
              assert len(cache) == 2  # two distinct entries

      def test_empty_filtered_corpus_does_not_crash(self, tmp_path):
          jl = tmp_path / "test.jsonl"
          records = [
              {"text": "news", "tags": ["новини"], "id": "1", "doc_id": "1"},
          ]
          self._write_jsonl(jl, records)
          paths = {"test_col": [jl]}
          cache: dict = {}
          with patch("retrieval.retriever._COLLECTION_PATHS", paths), \
               patch("retrieval.retriever._bm25_cache", cache):
              # Should not raise even though no docs match the filter
              ret = _get_bm25_retriever("test_col", {"tags": ["tutorial"]})
              assert ret is not None
  ```

  Note: `ret.docs` accesses the `BM25Retriever` internal list. If the LangChain version stores it differently, use `len(ret.invoke("any"))` to count results instead — adjust accordingly after running the tests.
  - Status:
  - Comments:

### 8. Extend `tests/test_retriever.py` — `hybrid_search` BM25 Filter Pass-through

- [ ] **Add `TestHybridSearchBM25FilterPassthrough` test class** — mock the BM25 factory to verify it receives the correct `filters` argument:
  ```python
  from unittest.mock import MagicMock, patch, call
  from langchain_core.documents import Document

  class TestHybridSearchBM25FilterPassthrough:
      """Verify hybrid_search passes filters to _get_bm25_retriever."""

      def _make_mock_docs(self, n: int = 1) -> list[Document]:
          return [
              Document(page_content=f"text {i}", metadata={"relevance_score": 0.9, "id": str(i), "doc_id": str(i)})
              for i in range(n)
          ]

      def test_no_filters_passes_none_to_bm25(self, monkeypatch):
          mock_bm25 = MagicMock()
          mock_bm25.invoke.return_value = self._make_mock_docs()
          mock_qdrant = MagicMock()
          mock_qdrant.invoke.return_value = self._make_mock_docs()

          with patch("retrieval.retriever._get_bm25_retriever", return_value=mock_bm25) as mock_factory, \
               patch("retrieval.retriever._QdrantRetriever", return_value=mock_qdrant), \
               patch("retrieval.retriever._get_reranker"), \
               patch("retrieval.retriever.get_embedder"):
              from retrieval.retriever import hybrid_search
              hybrid_search("тестовий запит", "articles")
              mock_factory.assert_called_once_with("articles", None)

      def test_tag_filter_passed_to_bm25(self, monkeypatch):
          mock_bm25 = MagicMock()
          mock_bm25.invoke.return_value = self._make_mock_docs()
          mock_qdrant = MagicMock()
          mock_qdrant.invoke.return_value = self._make_mock_docs()

          with patch("retrieval.retriever._get_bm25_retriever", return_value=mock_bm25) as mock_factory, \
               patch("retrieval.retriever._QdrantRetriever", return_value=mock_qdrant), \
               patch("retrieval.retriever._get_reranker"), \
               patch("retrieval.retriever.get_embedder"):
              from retrieval.retriever import hybrid_search
              hybrid_search("tutorial запит", "articles", filters={"tags": ["tutorial"]})
              mock_factory.assert_called_once_with("articles", {"tags": ["tutorial"]})

      def test_article_ref_auto_filter_passed_to_bm25(self, monkeypatch):
          mock_bm25 = MagicMock()
          mock_bm25.invoke.return_value = self._make_mock_docs()
          mock_qdrant = MagicMock()
          mock_qdrant.invoke.return_value = self._make_mock_docs()

          with patch("retrieval.retriever._get_bm25_retriever", return_value=mock_bm25) as mock_factory, \
               patch("retrieval.retriever._QdrantRetriever", return_value=mock_qdrant), \
               patch("retrieval.retriever._get_reranker"), \
               patch("retrieval.retriever.get_embedder"):
              from retrieval.retriever import hybrid_search
              # Query contains article ref → _extract_article_refs returns {"article_number": "17"}
              hybrid_search("стаття 17 закону", "laws")
              mock_factory.assert_called_once_with("laws", {"article_number": "17"})
  ```
  - Status:
  - Comments:

### 9. Extend `tests/test_retriever.py` — Score Threshold

- [ ] **Add `TestScoreThreshold` test class** — verify low-score results are dropped:
  ```python
  class TestScoreThreshold:
      def test_results_below_threshold_are_dropped(self, monkeypatch):
          """Chunks with relevance_score below rerank_score_threshold must be excluded."""
          from unittest.mock import patch
          from retrieval.retriever import hybrid_search
          from config import settings

          low_score_doc = Document(
              page_content="low quality",
              metadata={"relevance_score": 0.1, "id": "x", "doc_id": "x"},
          )
          high_score_doc = Document(
              page_content="high quality",
              metadata={"relevance_score": 0.9, "id": "y", "doc_id": "y"},
          )

          mock_pipeline = MagicMock()
          mock_pipeline.invoke.return_value = [low_score_doc, high_score_doc]

          with patch("retrieval.retriever.ContextualCompressionRetriever", return_value=mock_pipeline), \
               patch("retrieval.retriever._get_bm25_retriever"), \
               patch("retrieval.retriever._QdrantRetriever"), \
               patch("retrieval.retriever._get_reranker"), \
               patch("retrieval.retriever.get_embedder"), \
               patch.object(settings, "rerank_score_threshold", 0.3):
              results = hybrid_search("query", "laws")
              scores = [r.score for r in results]
              assert all(s >= 0.3 for s in scores)
              assert len(results) == 1  # only high_score_doc passes
  ```
  - Status:
  - Comments:

### 10. Create `scripts/validate_retrieval.py`

- [ ] **Create A/B validation script** — compares semantic-only vs full hybrid+rerank pipeline on 10 curated queries. Requires running Qdrant with ingested data:
  ```python
  """A/B validation: semantic-only vs hybrid+rerank retrieval pipeline.

  Usage: python scripts/validate_retrieval.py [--collection laws|articles]

  Requires: docker compose up -d && python -m ingest.run_ingest --collection all
  """

  from __future__ import annotations

  import argparse
  import sys
  from pathlib import Path

  # Allow running from repo root
  sys.path.insert(0, str(Path(__file__).parent.parent))

  from retrieval.retriever import hybrid_search
  from retrieval.embeddings import get_embedder
  from retrieval.qdrant_client import get_qdrant_client
  from config import settings

  _QUERIES_LAWS = [
      "Які вимоги до оголошення про проведення відкритих торгів за статтею 22?",
      "Підстави для відхилення тендерної пропозиції стаття 31",
      "Порядок оскарження рішень замовника до АМКУ стаття 18",
      "Строки укладання договору про закупівлю стаття 41",
      "Вимоги до документів, що підтверджують відповідність учасника критеріям відбору",
      "Умови застосування переговорної процедури закупівлі",
      "Порогові значення закупівель для товарів і послуг у 2024 році",
  ]

  _QUERIES_ARTICLES = [
      "Як зареєструватися на майданчику Prozorro?",
      "Що таке ЕДС і як підписати пропозицію електронним підписом?",
      "Як подати скаргу на рішення замовника в системі Prozorro?",
  ]


  def _semantic_only(query: str, collection: str, top_k: int = 5) -> list[dict]:
      """Run Qdrant-only search (no BM25, no reranking) for comparison baseline."""
      vector = get_embedder().embed_query(query)
      response = get_qdrant_client().query_points(
          collection_name=collection,
          query=vector,
          limit=top_k,
          with_payload=True,
      )
      return [
          {"id": p.payload.get("id", ""), "score": p.score, "text": p.payload.get("text", "")[:80]}
          for p in response.points
      ]


  def _run_comparison(queries: list[str], collection: str) -> None:
      print(f"\n{'='*80}")
      print(f"Collection: {collection} | Threshold: {settings.rerank_score_threshold}")
      print(f"{'='*80}\n")

      for i, query in enumerate(queries, 1):
          print(f"[{i}] {query[:90]}")

          semantic = _semantic_only(query, collection, top_k=5)
          hybrid = hybrid_search(query, collection, top_k=5)  # type: ignore[arg-type]

          sem_scores = [r["score"] for r in semantic]
          hyb_scores = [c.score for c in hybrid]

          sem_ids = {r["id"] for r in semantic}
          hyb_ids = {c.id for c in hybrid}
          new_in_hybrid = hyb_ids - sem_ids

          print(
              f"  Semantic-only : {len(semantic):2d} results | top={sem_scores[0]:.3f if sem_scores else 0:.3f}"
              f" | avg={sum(sem_scores)/len(sem_scores):.3f if sem_scores else 0:.3f}"
          )
          print(
              f"  Hybrid+rerank : {len(hybrid):2d} results | top={hyb_scores[0]:.3f if hyb_scores else 0:.3f}"
              f" | avg={sum(hyb_scores)/len(hyb_scores):.3f if hyb_scores else 0:.3f}"
              f" | new_docs={len(new_in_hybrid)}"
          )
          if new_in_hybrid:
              print(f"  BM25-only hits: {new_in_hybrid}")
          print()


  def main() -> None:
      parser = argparse.ArgumentParser(description="Validate hybrid vs semantic retrieval")
      parser.add_argument(
          "--collection",
          choices=["laws", "articles", "both"],
          default="both",
          help="Which collection to validate",
      )
      args = parser.parse_args()

      if args.collection in ("laws", "both"):
          _run_comparison(_QUERIES_LAWS, settings.qdrant_laws_collection)

      if args.collection in ("articles", "both"):
          _run_comparison(_QUERIES_ARTICLES, settings.qdrant_articles_collection)


  if __name__ == "__main__":
      main()
  ```
  - Status:
  - Comments:

### 11. Run Validation and Record Results

- [ ] **Run the A/B validation script** (requires running Qdrant with ingested data):
  ```bash
  docker compose up -d
  python -m ingest.run_ingest --collection all   # if not already ingested
  python scripts/validate_retrieval.py --collection both
  ```
  Record observations:
  - Does hybrid+rerank consistently outperform semantic-only?
  - How many queries show BM25-exclusive results (docs that semantic missed)?
  - Are there queries where score drops after reranking (BM25 noise)? If so, check whether BM25 pre-filtering fixes them.
  - Status:
  - Comments:

### 12. Update DELIVERY_CHECKLIST.md

- [ ] **Mark Phase 4.4 items complete** in `docs/DELIVERY_CHECKLIST.md`:
  - Change `- [ ] tags pre-filter для Technical Support (очікує Phase 2.3)` → `- [x]`
  - Change `- [ ] A/B вручну: semantic-only vs hybrid+rerank на 5-10 тестових запитах` → `- [x]`
  - Update Phase 4 milestone note to reflect completion
  - Status:
  - Comments:

### 13. Final Validation

- [ ] **Run all validation commands** — see Validation Commands section below.
  - Status:
  - Comments:

## Testing Strategy

**Unit tests** (fast, no external services):
- `TestFilterCacheKey` — 5 tests covering determinism, uniqueness, order-independence
- `TestMatchesBM25Filter` — 9 tests covering all filter semantics (scalar, list, nested, multi-key, missing fields)
- `TestBM25PreFiltering` — 4 tests using `tmp_path` with real JSONL files (no mocking of BM25, tests actual corpus filtering)
- `TestHybridSearchBM25FilterPassthrough` — 3 tests using mocked internals to verify `filters` flows correctly from `hybrid_search` to `_get_bm25_retriever`
- `TestScoreThreshold` — 1 test verifying post-rerank score filtering

**Existing tests preserved** — `TestExtractArticleRefs` (6 tests) and `TestChunkModel` (3 tests) remain unchanged.

**A/B validation** (requires live Qdrant, documents ingested):
- `scripts/validate_retrieval.py --collection both` — 10 queries, comparison table
- Validates that the fix improves BM25 recall for filtered queries

**No DeepEval tests in Phase 4** — these belong to Phase 8 (Testing) per the delivery checklist. Phase 4 only closes the implementation gaps; formal LLM-as-judge evaluation is Phase 8's scope.

## Acceptance Criteria

1. `python -m py_compile retrieval/retriever.py` exits 0.
2. `_matches_bm25_filter({"tags": ["tutorial"]}, {"tags": ["news"]})` returns `False`; `_matches_bm25_filter({"tags": ["tutorial"]}, {"tags": ["tutorial"]})` returns `True`.
3. `_get_bm25_retriever("articles", {"tags": ["tutorial"]})` and `_get_bm25_retriever("articles")` produce **different cache entries** (verified via `_bm25_cache` key count or `id()` comparison).
4. `_get_bm25_retriever("articles", {"tags": ["xyzzy_does_not_exist"]})` does not raise — returns a no-op retriever (empty corpus guard).
5. All 27+ unit tests in `tests/test_retriever.py` pass with `pytest tests/test_retriever.py -v`.
6. `scripts/validate_retrieval.py --collection laws` runs without error when Qdrant is running (exit 0).
7. Phase 4.4 items are marked `[x]` in `docs/DELIVERY_CHECKLIST.md`.

## Validation Commands

```bash
# 1. Syntax check
python -m py_compile retrieval/retriever.py
python -c "from retrieval.retriever import hybrid_search, _matches_bm25_filter, _filter_cache_key; print('imports OK')"

# 2. Unit tests (no external services needed)
pytest tests/test_retriever.py -v

# 3. Full test suite (nothing broken by the change)
pytest tests/ -q

# 4. A/B validation (requires running Qdrant + ingested data)
docker compose up -d
python scripts/validate_retrieval.py --collection both

# 5. Confirm graph still imports cleanly (smoke test for import chain)
python -c "from tools.rag import rag_search, make_rag_search_articles; print('rag tools OK')"
```

## Notes

- **Why BM25 filters matter at corpus load time, not query time**: BM25 is a bag-of-words model — it scores all documents in its index against the query. There is no way to filter results after scoring without re-implementing the merge step. The only correct approach is to pre-filter the corpus so only relevant documents enter the index. This is why the fix is in `_get_bm25_retriever` and not in the ensemble or reranker layer.
- **Cache memory trade-off**: Each unique `(collection, filter)` combination gets its own BM25 index in memory. For the current system (2 collections, 2–3 distinct filter values in production), this means at most 4–6 BM25 indices totalling ~50–200 MB. This is acceptable. If the filter space grows, consider switching to Qdrant native sparse vectors (listed as optional extension in the checklist).
- **Thread safety**: `_bm25_cache` is a plain dict — concurrent first-access from multiple threads could trigger duplicate corpus loading. The current system is single-threaded (REPL / single Slack handler) so this is acceptable for now. The fix does not worsen the existing thread-safety posture.
- **`bm25_ret.k` removal rationale**: `BM25Retriever` stores `k` as a plain attribute. Mutating the cached singleton after retrieval from cache is technically safe for single-threaded use (same value written each time), but it's dead code — `_get_bm25_retriever` already sets `k` to the same value. Removing it makes the locus of `k` control unambiguous.
- **No new library dependencies**: `json` (stdlib), already imported; `_filter_cache_key` uses `json.dumps` which is already available in the module via `import json`.
- **Empty document sentinel**: `[Document(page_content="", metadata={})]` passed to `BM25Retriever.from_documents` prevents the `ZeroDivisionError` in `rank_bm25`. The empty document contributes a 0-weight result that is trivially below `rerank_score_threshold` and will never appear in the final output. If you prefer, test with `BM25Retriever.from_documents([Document(page_content="")])` first — if `rank_bm25` still crashes on a single empty doc, use two empty docs instead.