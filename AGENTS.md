# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is a course-project scaffold for a Ukrainian public-procurement (ЕСЗ / Prozorro) support assistant.

The canonical design lives in **`docs/ARCHITECTURE.md`** (modules, Pydantic contracts, LangGraph nodes/edges, RAG, Slack, Langfuse, ADR). The implementation roadmap lives in **`docs/DELIVERY_CHECKLIST.md`** (Phase 0–9, vertical slices). README is a stub that links to both.

When asked to implement something, work from `docs/ARCHITECTURE.md` and the next pending checklist item in `docs/DELIVERY_CHECKLIST.md`. Both documents are in Ukrainian; the design intent is binding.

## Development principles

These three principles override personal style preferences. They apply to every change.

### Library-first

Before writing custom logic, check whether a library in the stack already provides it. The stack was chosen specifically for feature completeness — bypassing it usually means reinventing something worse.

Concrete preferences for this project:

- Structured output → `with_structured_output(SchemaModel)`, not manual JSON parsing.
- Tools → `@tool` decorator, not hand-rolled JSON schemas.
- Chunking → `RecursiveCharacterTextSplitter`, not custom splitters.
- Hybrid retrieval → `EnsembleRetriever` (LangChain) when its API fits; only hand-roll RRF if filters force it.
- BM25 → `langchain_community.retrievers.BM25Retriever` or `rank_bm25`, not a custom inverted index.
- Reranking → `langchain_classic.retrievers.document_compressors.CrossEncoderReranker`.
- Memory → `PostgresSaver` (LangGraph checkpointer), not custom serialization.
- Tracing → Langfuse `CallbackHandler`, not manual logging into Langfuse.
- Prompts → `langfuse.get_prompt(...).compile(...)`, not hardcoded strings.
- HITL → `HumanInTheLoopMiddleware` (LangChain agents), not custom interrupt logic.

If a library doesn't cover the case, custom code is fine — but the module's docstring must say *why* (one sentence). Do not silently reimplement framework features.

### Comments earn their place

Code should explain itself through naming and structure. Comments are added only when one of:

- They explain **why**, not **what** — business reason, link to an ADR, statute, or ticket.
- They document non-obvious external behavior (e.g. *"Tavily ignores `country` without `language`"*).
- They are `TODO` / `FIXME` with an owner and a clear next action.

Anti-patterns (do not write):

- Comments that restate the code (`# create the user` above `create_user(...)`).
- Section dividers (`# === Section ===`). Restructure the file instead.
- Commented-out code. Delete it; git keeps history.

### Cleanup is part of done

Implementation isn't complete until the workspace is clean. Before marking a checklist item `[x]`:

- Remove stubs, mock data, temporary `print` / `logger.debug` statements.
- Remove dead imports and unused symbols.
- Delete throwaway files (`scratch.py`, `test_local.py`, ad-hoc Jupyter notebooks left in the repo root).
- Sync `requirements.txt` (with version pins) and `.env.example` (with new keys + comments).
- If the implementation diverged from `docs/ARCHITECTURE.md`, update the architecture doc in the same change. Material decisions get a new ADR row in § 15.

The full per-item checklist is in **`docs/DELIVERY_CHECKLIST.md` → "Definition of Done"**. Run through it before closing any item.

## Reference patterns from lectures

Lecture-derived patterns are stored in **`docs/patterns/`** as compact, single-topic markdown files (one pattern per file, with minimal example + pitfalls). Use these as the authoritative source for framework APIs — they reflect the exact versions taught in the course, which is more reliable than memory for fast-moving libraries (LangChain 1.x, LangGraph, Langfuse, DeepEval).

Workflow:

- Before invoking a framework feature you haven't used in this repo yet, list `docs/patterns/` and read the matching file (e.g. `langgraph_fanout_with_send.md` before adding fan-out, `deepeval_geval_pattern.md` before writing a custom metric).
- References are the *first* place to look. Memory is the *last*.

## Common commands

```bash
# Python deps (Python 3.11+ recommended; LangChain >=1.2 and pydantic >=2.12 are pinned)
pip install -r requirements.txt

# Runtime infrastructure (Qdrant + Postgres for sessions/checkpointer)
docker compose up -d
docker compose down

# One-time: create LangGraph checkpointer schema in Postgres (idempotent)
python scripts/setup_postgres_checkpointer.py

# Source MariaDB (Prozorro infobox dump) — used ONLY by the export script
docker compose -f docker-compose.ingest.yml up -d   # starts local-prozorro-db on :3306
docker compose -f docker-compose.ingest.yml down

# Build datasets for ingestion (writes JSONL into data/)
python scripts/create_procurement_law_dataset.py   # → data/law/procurement_legal_dataset.jsonl
python scripts/export_infobox_db.py --output-dir data/infobox  # needs the ingest docker DB running

# Application entry point (Phase 0: echo REPL; real graph from Phase 1.7)
python main.py
```

The architecture references `deepeval test run tests/` for evaluation; the `tests/` directory exists but is empty until Phase 1.1.

## Architecture (target)

The system is a **LangGraph multi-agent pipeline** following Anthropic's *Orchestrator-Workers + Evaluator-Optimizer* pattern. The flow is hierarchical with a planning layer; quality of decomposition (Planner) and quality of critique (Critic) determine overall system quality.

```
Supervisor → Planner ──(off-topic)──→ static refusal → END
                    └─(needs_human)─→ Escalation → END
                    │
                    ▼ fan-out by SubTask.topic
            ┌───────┼────────────┐
         Lawyer  Common      Technical
         (laws) Support      Support
                (articles) (articles+web)
            └───────┼────────────┘
                    ▼
             aggregate sections
                    ▼
                 Critic ──(approve)──→ user
                       └─(revise, retries<N)─→ targeted re-run
                       └─(retries==N)────────→ Escalation
```

Key invariants to preserve when editing:

- **Three-domain scope** (technical / procurement_general / legal). Off-topic filtering is *defense in depth* — Planner gate (`is_on_topic`), per-agent system prompts, and Critic's Structure dimension. Don't collapse these layers; each catches what the previous misses.
- **Inter-agent contracts are Pydantic models** (`ResearchPlan`, `SubTask`, `WorkerResponse`, `CritiqueResult`, `EscalationOutput`). These belong in `schemas.py`. Agents communicate via these structured outputs, not free text.
- **Two RAG collections, not one**: `laws` (large chunks, article-level) for the Lawyer, `articles` (smaller chunks with overlap) for Common/Technical Support. Technical Support pre-filters `articles` by `tags` against the `TECH_SUPPORT_TAG_WHITELIST` from `.env` (the exact whitelist is finalized after dataset analysis — see ADR / Open TODOs). Don't merge the two collections.
- **Retrieval is hybrid + reranked, not semantic-only**: every RAG call goes through semantic search + BM25 → ensemble (RRF) → cross-encoder rerank (`BAAI/bge-reranker-base`) → score-threshold filter. The Lawyer additionally pre-filters by `article_number` when the query contains a statute reference. Don't bypass the hybrid pipeline by calling Qdrant or BM25 directly from agents — go through `tools/rag.py`.
- **Critic's `revise` is targeted** — it returns `revision_requests=[{topic, request}]` and the Supervisor only re-runs the named workers, not the whole graph.
- **Escalation has two trigger paths**: Planner sets `needs_human=true` (skip workers/Critic entirely), or Critic exhausts `CRITIC_MAX_RETRIES`. Both produce the same `EscalationOutput` to a Slack expert channel + audit-trail file.
- **Sessions** use `langgraph-checkpoint-postgres` (`PostgresSaver`); session ID is `team_id:channel_id:user_id[:thread_ts]`.
- **Web search** is Tavily, hardcoded `language=uk, country=UA`, with post-filter for non-Ukrainian results. Technical Support uses an `allowed_domains` whitelist; Common Support does not.
- **Prompts live in Langfuse Prompt Management**, not in code. The `prompts/` directory is a backup copy, not the source of truth at runtime.

## Data pipeline

`data/law/procurement_legal_dataset.jsonl` is built by `scripts/create_procurement_law_dataset.py`, which scrapes `zakon.rada.gov.ua` for a fixed list of laws/resolutions (Закон 922, КМУ 1178, 1275, 166, ...) and chunks them at ~2000 chars (sized for cl100k Ukrainian tokenization, leaving headroom under the 512-token limits of BGE-M3 / multilingual-e5).

`data/infobox/*.jsonl` is built by `scripts/export_infobox_db.py`, which shells out to `docker compose -f docker-compose.ingest.yml exec mariadb mysql ...` against the `prozorro` database loaded from `prozorro_backup.sql` (this SQL dump is *not* in the repo — it must be placed alongside `docker-compose.ingest.yml` for the DB to initialize).

Runtime ingestion into Qdrant lands in Phase 1.3 as `ingest/run_ingest.py` (the package directory `ingest/` already exists from Phase 0).

## Configuration

`config.py` declares the full Pydantic `Settings(BaseSettings)` from `docs/ARCHITECTURE § 11` (LLM, Tavily, Qdrant, Postgres, Slack, Langfuse, behavior limits, freshness thresholds). Secrets are `Optional[SecretStr]` so `Settings()` validates with an empty `.env`; components assert their own required keys when first used. CSV-valued fields (`tech_support_allowed_domains`, `tech_support_tag_whitelist`) are split via a `field_validator`. The canonical env-key list is in `.env.example`. Never read `os.environ` outside `config.py`.