---
description: Use when you have a plan file ready and need to implement it into the codebase
argument-hint: [path-to-plan]
---

# Implement

Follow the `Workflow` to implement the `PATH_TO_PLAN` then `Report` the completed work.

## Instructions

- IMPORTANT: Implement the plan top to bottom, in order. Do not skip any steps. Do not stop in between steps. Complete every step in the plan before stopping.
  - Make your best guess judgement based on the plan, everything will be detailed there.
  - If you have not run any validation commands throughout your implementation, DO NOT STOP until you have validated the work.
  - Your implementation should end with executing the validation commands to validate the work, if there are issues, fix them before stopping.

## Project-Specific Implementation Patterns

This is a Python LangGraph multi-agent system for Ukrainian public procurement (ЕСЗ / Prozorro) support. Architecture is **Orchestrator-Workers + Evaluator-Optimizer** (Anthropic). Read `README.md` and `CLAUDE.md` for the binding design.

### Module Layout (root-level modules)
- `agent.py` — LangGraph graph wiring (Supervisor / Planner / workers / Critic / Escalation nodes)
- `schemas.py` — Pydantic contracts (`ResearchPlan`, `SubTask`, `WorkerResponse`, `CritiqueResult`, `EscalationOutput`)
- `retriever.py` — hybrid retrieval (semantic + BM25 + cross-encoder rerank); two collections: `laws` and `articles`
- `ingest.py` — JSONL → vector store ingestion
- `tools.py` — `web_search` (Tavily UA), `read_url`, `knowledge_search`, `write_report`
- `config.py` — Pydantic `BaseSettings` from `.env` (extend, don't fork)
- `main.py` — REPL entry point
- `prompts/` — backup copy of agent prompts (Langfuse Prompt Management is the runtime source)
- `scripts/` — real, runnable data-pipeline scripts (do not stub)
- `data/law/`, `data/infobox/` — JSONL datasets produced by `scripts/`

### Invariants (do not violate)
- **Three-domain scope**: `technical_system` / `procurement_general` / `legal`. Off-topic filtering is *defense in depth* — Planner gate, per-agent system prompts, Critic Structure dimension. Don't collapse the layers.
- **Inter-agent contracts are Pydantic**, not free text. New agents communicate via models in `schemas.py`.
- **Two RAG collections**: `laws` (article-level chunks, Lawyer only) and `articles` (smaller chunks, Common/Technical Support). Technical Support filters `articles` by `subcategory=tutorial`. Don't merge.
- **Critic `revise` is targeted** — re-runs only workers named in `revision_requests`, not the whole graph.
- **Escalation has two trigger paths**: Planner `needs_human=true` (skip workers/Critic) OR Critic exhausts `CRITIC_MAX_RETRIES`. Both produce `EscalationOutput` to Slack + audit-trail file.
- **Sessions**: `langgraph-checkpoint-postgres` `PostgresSaver`. Session ID = `team_id:channel_id:user_id[:thread_ts]`.
- **Web search**: Tavily, hardcoded `language=uk, country=UA`, post-filter non-Ukrainian. Technical Support uses `allowed_domains` whitelist; Common Support does not.
- **Prompts live in Langfuse** at runtime. The `prompts/` directory is a backup; don't treat it as canonical.

### Code Patterns
- Python 3.11+. LangChain `>=1.2`, pydantic `>=2.12`, pydantic-settings `>=2.12` (pinned in `requirements.txt`).
- Add new dependencies with `pip install <pkg>` and update `requirements.txt` (no `pyproject.toml` / no `uv` here).
- Type-hint everything; Pydantic v2 models for all structured I/O between graph nodes.
- Module-level `logger = logging.getLogger(__name__)`; structured logs with the session ID and node name.
- Secrets via `SecretStr` in `Settings`; never hardcode keys or read `os.environ` directly outside `config.py`.
- Don't stub with `...`/`pass` once a module is being implemented — finish it or skip it. Don't leave half-stubs around real code.

### Standard Implementation Phases
1. **Schemas** — Add or extend Pydantic models in `schemas.py` first; downstream code depends on these.
2. **Config** — Extend `Settings` in `config.py` with any new env keys (Tavily, Postgres, Slack, Langfuse, `CRITIC_MAX_RETRIES`, `WORKER_TIMEOUT_SECONDS`, `PLANNER_MAX_SUBTASKS`).
3. **Tool / retriever / agent node** — Implement against the new schema. Keep node functions pure where possible (read state → return state delta).
4. **Graph wiring** — Update `agent.py` to add the node and edges per the README flow.
5. **Prompts** — Update `prompts/<agent>.md` (backup) AND push to Langfuse if the prompt has changed at runtime.
6. **Data pipeline** — Only touch `scripts/` and `ingest.py` if the change requires re-ingesting; mention re-ingestion in the report.
7. **Tests / eval** — Add unit tests in `tests/` and LLM evals in `tests/eval/` (create the directory if it doesn't exist).
8. **Validation** — Run the validation commands below.

### Validation Commands
```bash
python -m py_compile agent.py ingest.py retriever.py tools.py main.py config.py  # syntax check
python -c "from agent import agent; print(type(agent))"                          # graph imports cleanly
python ingest.py                                                                 # rebuild index (only if data/ or chunking changed)
pytest tests/ -q                                                                  # unit tests (create tests/ first if missing)
deepeval test run tests/eval/                                                     # LLM evaluation (create tests/eval/ first if missing)
```

If your change touches the docker-backed data pipeline:
```bash
docker compose up -d                                                              # start local-prozorro-db on :3306
python scripts/export_infobox_db.py --output-dir data/infobox
docker compose down
```

## The Iron Law

```
NO COMPLETION CLAIM WITHOUT VERIFIED EVIDENCE
```

Claiming completion without running validation? Start over.

**No exceptions:**
- Don't claim "should work" - prove it works
- Don't trust previous run results - run again
- Don't skip validation "this once"
- Evidence or it didn't happen

## Verification Gate (MANDATORY)

BEFORE claiming implementation is complete:

1. **IDENTIFY**: What validation commands prove completion?
2. **RUN**: Execute EVERY validation command (fresh, complete)
3. **READ**: Full output - check exit codes, count failures
4. **VERIFY**: Does ALL output confirm success?
   - If NO: Fix issues, re-run, repeat
   - If YES: Include evidence in report
5. **ONLY THEN**: Claim completion

Skip any step = incomplete implementation. Return to Step 1.

**Evidence required for completion claim:**
- Validation command output (actual output, not "it passed")
- Test results with pass/fail counts
- Git diff summary

## Red Flags - STOP Implementation

If any of these thoughts occur to you, STOP and reconsider:

- Writing code before reading relevant files
- Skipping validation "because code looks correct"
- "I'll fix the tests later"
- Committing without running checks
- "Just a small change, no need to verify"
- Using "should work" or "probably passes"
- Claiming completion before running commands
- Trusting previous run results

**If any of these apply: STOP. Run validation commands NOW.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Code is obviously correct" | Obvious code fails all the time. Verify. |
| "Tests were passing earlier" | Previous runs prove nothing. Run again. |
| "Just a small change" | Small changes break things. Full verification. |
| "I'll test it later" | Later never comes. Test now. |
| "The plan said to do this" | Plans can be wrong. Verify outcomes. |

## Announcement (MANDATORY)

Before starting work, announce:

"I'm using /implement to implement the plan at [path]. I will follow the workflow exactly and verify all work before claiming completion."

This creates commitment. Skipping this step = likely to skip other steps.

## Variables

PATH_TO_PLAN: $ARGUMENTS

## Workflow

- If no `PATH_TO_PLAN` is provided, STOP immediately and ask the user to provide it.

  **No exceptions:**
  - Don't infer the plan from conversation
  - Don't create an ad-hoc plan
  - Don't proceed without an explicit path
  - STOP means STOP

- Read the plan at `PATH_TO_PLAN`. Ultrathink about the plan and IMPLEMENT it into the codebase.
  - Implement the entire plan top to bottom before stopping.

## Report

- Summarize the work you've just done in a concise bullet point list.
- Report the files and total lines changed with `git diff --stat`
