# Multi-agent: Orchestrator-Workers + Evaluator-Optimizer

## When to use

When a task naturally decomposes into independent sub-tasks (each can be done in parallel by a specialist) AND when output quality benefits from a separate critique pass with revisable feedback.

Anthropic's "Building Effective Agents" defines these as two patterns; we **combine** them in this project:

- **Orchestrator-Workers** — Supervisor (orchestrator) plans subtasks, dispatches to workers, collects outputs.
- **Evaluator-Optimizer** — a Critic agent reviews the output and asks for revisions; the loop continues until approval or max retries.

This is *the* architecture of our project. It's strictly more powerful than simple Routing (one classifier → one specialist) and worth the coordination tax for our use case (multi-domain procurement queries with quality stakes).

## Conceptual flow

```
Input → Planner ──(decompose)──→ [SubTask, SubTask, ...]
                                       │
                                       ▼ fan-out (Send API)
                              ┌────────┼────────┐
                            Worker  Worker   Worker
                              └────────┼────────┘
                                       ▼ aggregate
                                    Critic ──(approve)──→ Output
                                          └─(revise)────┐
                                                        ▼
                                              targeted re-dispatch
                                              (only flagged workers)
                                                        │
                                                        └──► Critic again
```

## When NOT to use

- **Single-domain queries with no quality bar to enforce** — Routing is enough.
- **Tasks that don't decompose** — sequential reasoning where each step needs the previous step's full output. Use Plan-and-Execute or just `create_agent` with tools.
- **Cost/latency-critical paths** — every Critic loop adds ~2× the LLM cost of the underlying specialists. Don't add Critic on hot paths unless quality is the bottleneck.

## Pitfalls

- **Targeted re-dispatch is the optimization.** When Critic says "revise: legal section incomplete", only re-run the Lawyer worker. Re-running the entire fan-out wastes tokens and time. Implement this from day one — it's not premature optimization, it's correctness (avoids the Common Support agent inadvertently changing its already-approved section).
- **Worker isolation.** Each worker should not know it runs in parallel with siblings. Pass each worker only its `SubTask` (via `Send`), not the full state. Workers that depend on siblings' output → it's a sequential pipeline, not Orchestrator-Workers.
- **Aggregation is NOT an LLM step in our project.** We assemble Markdown sections deterministically (concatenation with section headers, skipping empty sections). LLM-based aggregation introduces drift in approved content.
- **Critic must be allowed to escalate, not just approve/revise.** Without an exit criterion (max retries → escalate to human), revise loops can run indefinitely on hard queries. `CRITIC_MAX_RETRIES` from `.env`.
- **Critic's feedback must be actionable per-worker.** "The whole answer is bad" is unusable. Force structured `revision_requests=[{topic, request}]` (Pydantic) so the Supervisor knows exactly what to re-dispatch.
- **The "Multi-Agent Coordination Tax"** is real (Anthropic, Microsoft research). Budget for ~3-5× the latency of a single-agent solution. If that's unacceptable, this isn't the right pattern.

## Source

- Anthropic: ["Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) — the canonical reference.
- `lesson-7.md` — Orchestrator-Workers (Section 1.2), Evaluator-Optimizer (Section 1.2 + Exercise 1).
- Project-specific: this is wired into `ARCHITECTURE.md § 5` as the LangGraph topology.
