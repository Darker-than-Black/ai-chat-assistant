# Plan: Phase 1 — Vertical Slice #1: Single Lawyer Agent

## Task Description

Implement Phase 1 of the Prozorro procurement support assistant: a single Lawyer agent that
accepts Ukrainian legal questions via CLI, retrieves relevant procurement law chunks via a
**hybrid retrieval pipeline** (semantic + BM25 → RRF ensemble → cross-encoder rerank), and
returns a structured `WorkerResponse` with answer and source citations.

No orchestration (Planner/Critic/Escalation), no Slack, no checkpointer — the minimal
end-to-end path from query to structured answer.

Covers DELIVERY_CHECKLIST items **1.1 → 1.7** (7 sequential sub-tasks).

---

## Objective

`python main.py` accepts a Ukrainian natural-language question about public procurement law,
runs it through the hybrid retrieval pipeline over Qdrant (`laws` collection), and prints a
structured `WorkerResponse` with answer text, confidence, and source citations. All retrieval
goes through `tools/rag.py` — never directly to Qdrant or BM25 from agents.

---

## Solution Approach

Build in strict dependency order: **schemas first** (contracts), then retrieval infrastructure
(embeddings + Qdrant client + BM25 + reranker + hybrid pipeline), then ingestion, then RAG
tool, then Lawyer agent, then main.py wiring.

### Architecture Decisions

- **Affected graph nodes**: Only the Lawyer worker node. No StateGraph in Phase 1 — the agent
  is called directly from `invoke_lawyer()`. Full graph wiring starts in Phase 2.
- **Schemas**: `Source`, `WorkerResponse`, `SubTask`, `ResearchPlan`, `CritiqueResult`,
  `EscalationOutput`, `GraphState` all defined in `schemas.py`. `GraphState` is unused in Phase
  1 but must have the correct shape for Phase 2 nodes.
- **RAG collection(s)**: `laws` collection only. All retrieval goes through `tools/rag.py` →
  `retrieval/retriever.hybrid_search()`. Never call Qdrant or BM25 directly from agents.
- **Hybrid pipeline** (mandatory per CLAUDE.md invariant):
  `semantic (QdrantRetriever) + BM25 (BM25Retriever) → EnsembleRetriever (RRF) →
  ContextualCompressionRetriever (CrossEncoderReranker, BAAI/bge-reranker-base) →
  score-threshold filter → top-k`
- **Article pre-filter**: Lawyer auto-detects statute references in the query (e.g., "стаття
  17") and passes them as Qdrant payload filter to narrow vector search.
- **External calls**: OpenAI for embeddings + LLM. No Tavily, no Slack.
- **Sessions**: No checkpointer in Phase 1. PostgresSaver introduced in Phase 2.
- **Prompt source**: `prompts/lawyer.md` loaded at startup. Langfuse Prompt Management
  integration is Phase 3.

---

## Relevant Files

### Existing Files

- `config.py` — `settings.embedding_model`, `settings.qdrant_url`, `settings.qdrant_laws_collection`,
  `settings.retrieval_top_k` (20), `settings.hybrid_semantic_weight` (0.6),
  `settings.hybrid_bm25_weight` (0.4), `settings.reranker_model`, `settings.rerank_top_k` (5),
  `settings.rerank_score_threshold` (0.3), `settings.llm_model`, `settings.llm_provider`
- `main.py` — Phase-0 echo REPL; updated in Step 7
- `data/law/procurement_legal_dataset.jsonl` — 3.5 MB; fields: `id, doc_id, title, type,
  authority, domain, source, source_url, version_date, date_fetched, section_index,
  chunk_index, section_heading, breadcrumb, article_number, part_number,
  paragraph_number, doc_amendments_removed_count, text`
- `data/infobox/articles.jsonl`, `faq.jsonl`, `courses.jsonl` — 22 MB; fields:
  `id, doc_id, title, type, date_published, tags, chunk_index, text`
- `docs/ARCHITECTURE.md` — binding spec § 4 (schemas), § 6 (RAG), § 11 (config)
- `docs/DELIVERY_CHECKLIST.md` — Phase 1 items 1.1–1.7
- `requirements.txt` — `langchain>=1.2`, `langchain-classic>=1.0`, `langchain-community>=0.4`,
  `langgraph>=0.6`, `qdrant-client>=1.13`, `rank_bm25>=0.2.2`, `sentence-transformers>=3.0`

### New Files to Create

- `schemas.py` — All Pydantic contracts + `GraphState`
- `retrieval/embeddings.py` — OpenAI embeddings wrapper, batch support
- `retrieval/qdrant_client.py` — Singleton `QdrantClient` + `ensure_collections()`
- `retrieval/retriever.py` — `hybrid_search()`: QdrantRetriever + BM25 + EnsembleRetriever +
  CrossEncoderReranker + score-threshold; `_extract_article_refs()` for query parsing
- `ingest/chunkers.py` — `chunk_law()` (pass-through), `chunk_article()` (RecursiveCharacterTextSplitter)
- `ingest/pipeline.py` — JSONL → embed → upsert
- `ingest/run_ingest.py` — CLI: `python -m ingest.run_ingest --collection laws|articles|all`
- `tools/rag.py` — `@tool rag_search(query, collection)` calling `hybrid_search`
- `agents/lawyer.py` — `build_lawyer_agent()` with `create_react_agent` + `response_format`
- `prompts/lawyer.md` — Lawyer system prompt (Ukrainian)
- `tests/conftest.py` — Shared fixtures
- `tests/test_schemas.py` — Pydantic validator unit tests
- `tests/test_retriever.py` — `_extract_article_refs` unit tests + `Chunk` model tests

---

## Implementation Phases

- [ ] **Phase A: Foundation** — `schemas.py`, `tests/test_schemas.py`, `tests/conftest.py`
  - Status:
  - Comments:

- [ ] **Phase B: Retrieval Infrastructure** — `retrieval/embeddings.py`,
  `retrieval/qdrant_client.py`, `retrieval/retriever.py`
  - Status:
  - Comments:

- [ ] **Phase C: Ingestion** — `ingest/chunkers.py`, `ingest/pipeline.py`, `ingest/run_ingest.py`
  - Status:
  - Comments:

- [ ] **Phase D: Agent Layer** — `tools/rag.py`, `prompts/lawyer.md`, `agents/lawyer.py`
  - Status:
  - Comments:

- [ ] **Phase E: Integration** — Update `main.py`; run ingestion; end-to-end test
  - Status:
  - Comments:

---

## Step by Step Tasks

### 1. Pydantic Schemas

- [ ] **Create `schemas.py`** — All 7 contracts from ARCHITECTURE § 4
  ```python
  class Source(BaseModel):
      title: str
      url: str | None = None
      doc_id: str
      metadata: dict = Field(default_factory=dict)

  class WorkerResponse(BaseModel):
      topic: Literal["legal", "procurement_general", "technical_system"]
      found: bool
      answer: str | None = None
      sources: list[Source] = Field(default_factory=list)
      confidence: float = Field(ge=0.0, le=1.0)
      needs_human: bool = False
      needs_human_reason: str | None = None

  class SubTask(BaseModel):
      topic: Literal["legal", "procurement_general", "technical_system"]
      query: str
      rationale: str

  class ResearchPlan(BaseModel):
      is_on_topic: bool
      off_topic_reason: str | None = None
      language: Literal["uk", "en"] = "uk"
      original_query: str
      subtasks: list[SubTask] = Field(default_factory=list)
      needs_human: bool = False
      escalation_reason: str | None = None

      @model_validator(mode="after")
      def validate_consistency(self) -> "ResearchPlan":
          # three invariants from ARCHITECTURE § 4.4
          if not self.is_on_topic and self.subtasks:
              raise ValueError("off-topic plan must have empty subtasks")
          if self.needs_human and not self.escalation_reason:
              raise ValueError("needs_human=True requires escalation_reason")
          if self.is_on_topic and not self.needs_human and not self.subtasks:
              raise ValueError("on-topic plan must have at least one subtask")
          return self

  class CritiqueResult(BaseModel):
      verdict: Literal["approve", "revise", "escalate"]
      revision_requests: list[dict] = Field(default_factory=list)
      dimensions: dict = Field(default_factory=dict)
      summary: str = ""

  class EscalationOutput(BaseModel):
      reason: str
      original_query: str
      session_id: str
      timestamp: str

  class GraphState(TypedDict):          # defined now, used from Phase 2
      user_message: str
      session_id: str
      user_id: str
      plan: ResearchPlan | None
      worker_responses: Annotated[list[WorkerResponse], operator.add]
      critic_history: list[CritiqueResult]
      retry_count: int
      aggregated_response: str | None
      escalated: bool
      final_response: str | None
  ```
  - Status:
  - Comments:

- [ ] **Create `tests/conftest.py`** — Shared fixtures
  - Status:
  - Comments:

- [ ] **Create `tests/test_schemas.py`** — Unit tests for all validators
  - `WorkerResponse`: confidence 0.0/0.5/1.0 valid; 1.1 and -0.1 raise `ValidationError`
  - `ResearchPlan`: off-topic + non-empty subtasks raises; `needs_human=True` + no reason raises;
    on-topic + empty subtasks raises; valid off-topic passes; valid on-topic + subtask passes
  - `Source`: url optional
  - Status:
  - Comments:

### 2. Embeddings + Qdrant Client

- [ ] **Create `retrieval/embeddings.py`** — OpenAI embeddings, batch=100
  - `EmbeddingModel` wraps `langchain_openai.OpenAIEmbeddings`
  - `embed_texts(list[str]) -> list[list[float]]` batches by 100
  - `embed_query(str) -> list[float]`
  - Lazy module singleton `get_embedder() -> EmbeddingModel`
  - Status:
  - Comments:

- [ ] **Create `retrieval/qdrant_client.py`** — Singleton client + collection creation
  - `_VECTOR_SIZES = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}`
  - `get_qdrant_client() -> QdrantClient` lazy singleton
  - `ensure_collections()` — idempotent; uses `Distance.COSINE`
  - Status:
  - Comments:

### 3. Hybrid Retriever

- [ ] **Create `retrieval/retriever.py`** — Full hybrid pipeline
  - `class Chunk(BaseModel)`: `id, doc_id, text, metadata, score`
  - `class _QdrantRetriever(BaseRetriever)`: `collection`, `filters`, `top_k=20`;
    builds Qdrant `Filter(must=[FieldCondition(key=k, match=MatchValue(value=v))])` from filters dict;
    returns `list[Document]` (page_content=payload["text"], metadata=full payload)
  - BM25 cache: `_bm25_cache: dict[str, BM25Retriever]`; `_get_bm25_retriever(collection)` loads
    JSONL from `_COLLECTION_PATHS[collection]` on first call; uses `BM25Retriever.from_documents(docs)`
  - Reranker singleton: `_get_reranker()` builds
    `CrossEncoderReranker(model=HuggingFaceCrossEncoder(settings.reranker_model), top_n=settings.rerank_top_k)`
  - `_extract_article_refs(query: str) -> dict | None` — regex `(?:стаття|ст\.?)\s*(\d+)`,
    returns `{"article_number": match}` or `None`
  - `hybrid_search(query, collection, filters=None, top_k=None) -> list[Chunk]`:
    1. Laws collection: auto-detect article refs via `_extract_article_refs` when `filters=None`
    2. Build `_QdrantRetriever(collection, filters, top_k=settings.retrieval_top_k)`
    3. Get `bm25_ret = _get_bm25_retriever(collection)`; set `bm25_ret.k = settings.retrieval_top_k`
    4. `ensemble = EnsembleRetriever([qdrant_ret, bm25_ret], weights=[semantic_w, bm25_w])`
    5. `pipeline = ContextualCompressionRetriever(base_compressor=_get_reranker(), base_retriever=ensemble)`
    6. `docs = pipeline.invoke(query)`
    7. Filter by `relevance_score >= settings.rerank_score_threshold`; slice `[:top_k]`
    8. Convert to `list[Chunk]`
  - Imports: `from langchain_classic.retrievers.document_compressors import CrossEncoderReranker`,
    `from langchain_community.cross_encoders import HuggingFaceCrossEncoder`,
    `from langchain_community.retrievers import BM25Retriever`,
    `from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever`
  - Status:
  - Comments:

- [ ] **Create `tests/test_retriever.py`** — Unit tests for pure functions
  - `_extract_article_refs`: "стаття 17" → `{"article_number": "17"}`; "ст. 22" → `{"article_number": "22"}`; "загальне питання" → `None`; "СТАТТЯ 5" → `{"article_number": "5"}`
  - `Chunk` model: valid construction; score and metadata fields
  - Status:
  - Comments:

### 4. Ingestion Pipeline

- [ ] **Create `ingest/chunkers.py`**
  - `chunk_law(record: dict) -> list[dict]` — pass-through: `return [record]`
  - `chunk_article(record: dict) -> list[dict]` — `RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)`;
    for each split: inherit parent fields, set `chunk_index=i`, regenerate `id=sha256(f"{doc_id}-{i}")`
  - Status:
  - Comments:

- [ ] **Create `ingest/pipeline.py`** — JSONL → embed → upsert
  - `ingest_collection(collection: Literal["laws","articles"]) -> dict`
  - Laws embedding text: `f"{breadcrumb}\n{section_heading}\n{text}"`
  - Articles embedding text: `f"{title}\n{' '.join(tags)}\n{text}"`
  - Batch of 100: embed → build `PointStruct(id=chunk["id"], vector=v, payload=chunk)` → upsert
  - Print progress every 500 chunks
  - Returns `{"collection": name, "chunks_ingested": N}`
  - Status:
  - Comments:

- [ ] **Create `ingest/run_ingest.py`** — CLI
  - `argparse --collection {laws,articles,all}` (default `all`)
  - Calls `ensure_collections()` then `ingest_collection(...)` for each
  - Run as: `python -m ingest.run_ingest --collection laws`
  - Status:
  - Comments:

### 5. RAG Tool

- [ ] **Create `tools/rag.py`**
  ```python
  @tool
  def rag_search(query: str, collection: str = "laws") -> str:
      """Search the procurement knowledge base.
      collection='laws' for procurement law/regulations.
      collection='articles' for Prozorro platform procedures.
      """
  ```
  - Calls `hybrid_search(query, collection, top_k=settings.rerank_top_k)`
  - Formats each chunk: `---\n{breadcrumb or title}\n{text}\nДжерело: {source_url or doc_id}`
  - Truncates to 6000 chars total
  - Status:
  - Comments:

### 6. Lawyer Agent

- [ ] **Create `prompts/lawyer.md`** — Ukrainian system prompt
  - Role: senior procurement law specialist
  - Laws in scope: Закон 922, 808; КМУ 1178, 1275, 166, 822
  - Instruction: always call `rag_search(collection="laws")` before answering
  - Instruction: cite article number + breadcrumb from sources
  - Output: `WorkerResponse` with topic="legal", found, answer (Ukrainian), sources, confidence 0–1,
    needs_human (true only for specialist legal opinion), needs_human_reason
  - Scope: off-topic → found=false with explanation
  - Status:
  - Comments:

- [ ] **Create `agents/lawyer.py`**
  - `get_llm() -> BaseChatModel` — reads `settings.llm_provider/model/api_key`
  - `_load_system_prompt() -> str` — reads `prompts/lawyer.md`; docstring notes Phase 3 Langfuse migration
  - `build_lawyer_agent() -> CompiledGraph` — `create_react_agent(model, [rag_search], state_modifier=prompt, response_format=WorkerResponse)`
  - `get_lawyer_agent()` — lazy singleton
  - `invoke_lawyer(query: str) -> WorkerResponse` — `agent.invoke({"messages": [HumanMessage(query)]})["structured_response"]`
  - Status:
  - Comments:

### 7. REPL Integration

- [ ] **Update `main.py`** — replace echo with `invoke_lawyer`
  - Import `invoke_lawyer` from `agents.lawyer`
  - `response = invoke_lawyer(user_input)` → format and print WorkerResponse
  - Show answer, confidence, sources, escalation notice if `needs_human`
  - Keep Phase-0 exit handling (EOF, KeyboardInterrupt, exit/quit)
  - Status:
  - Comments:

### 8. Run Ingestion

- [ ] **Populate Qdrant `laws` collection**
  - Prereqs: `docker compose up -d`; `OPENAI_API_KEY` in `.env`
  - `python -m ingest.run_ingest --collection laws`
  - Verify at `http://localhost:6333/dashboard`
  - Status:
  - Comments:

---

## Testing Strategy

**Unit tests (no external deps):**
- `tests/test_schemas.py` — All Pydantic validators
- `tests/test_retriever.py` — `_extract_article_refs` pure function; `Chunk` model

**Integration (requires Docker + OpenAI key + BM25/reranker first load):**
- `python -m ingest.run_ingest --collection laws`
- `python main.py` → ask "Що таке тендерна документація за Законом 922?"

---

## Acceptance Criteria

1. `python -m py_compile schemas.py retrieval/embeddings.py retrieval/qdrant_client.py retrieval/retriever.py ingest/chunkers.py ingest/pipeline.py tools/rag.py agents/lawyer.py main.py` exits 0
2. `python -c "from schemas import WorkerResponse, ResearchPlan, GraphState; print('OK')"` prints OK
3. `pytest tests/test_schemas.py tests/test_retriever.py -q` — all green, no external deps
4. `python -m ingest.run_ingest --collection laws` completes and reports >0 chunks (needs Qdrant + OpenAI key)
5. `python main.py` returns a structured WorkerResponse with non-empty answer and ≥1 Source (needs indexed Qdrant + OpenAI key)
6. Response satisfies `WorkerResponse` validation — confidence 0–1, topic="legal"

---

## Validation Commands

```bash
python -m py_compile schemas.py \
  retrieval/embeddings.py retrieval/qdrant_client.py retrieval/retriever.py \
  ingest/chunkers.py ingest/pipeline.py \
  tools/rag.py agents/lawyer.py main.py

python -c "from schemas import Source, WorkerResponse, SubTask, ResearchPlan, \
  CritiqueResult, EscalationOutput, GraphState; print('schemas OK')"

python -c "from agents.lawyer import build_lawyer_agent; print('lawyer OK')"

pytest tests/test_schemas.py tests/test_retriever.py -q

# Requires: docker compose up -d, OPENAI_API_KEY in .env
python -m ingest.run_ingest --collection laws

# Requires: indexed Qdrant, OPENAI_API_KEY
python main.py
```

---

## Notes

- **No StateGraph in Phase 1**: `build_lawyer_agent()` calls `create_react_agent` which
  returns a `CompiledGraph` internally, but `invoke_lawyer()` treats it as a black-box
  runnable. The full multi-node `StateGraph` starts in Phase 2.
- **`GraphState` defined now but unused**: Must have correct shape for Phase 2 contracts.
- **Law chunk IDs are final**: `scripts/create_procurement_law_dataset.py` generates SHA256
  IDs. `chunk_law()` passes them through unchanged.
- **BM25 first-load cost**: `_get_bm25_retriever("laws")` reads the full 3.5 MB JSONL on
  first query — expect 1–3 seconds startup latency on initial call. Cached for all subsequent
  queries in the same process.
- **Reranker model download**: `BAAI/bge-reranker-base` is downloaded from HuggingFace Hub on
  first use (~200 MB). Subsequent runs use the local cache (`~/.cache/huggingface`).
- **OpenAI key required for embeddings** even if `LLM_PROVIDER=anthropic`.
- **`response_format` in `create_react_agent`**: Result key is `"structured_response"`.
  Available in `langgraph>=0.2.20` (well within the `>=0.6` pin).
- **`langchain_classic` import**: `CrossEncoderReranker` path per CLAUDE.md. If import fails,
  check `langchain.retrievers.document_compressors` as alternative location.
- **No new pip packages**: All deps already in `requirements.txt`.