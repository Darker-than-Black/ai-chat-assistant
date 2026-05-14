# Plan: Phase 3 — Fan-out + Critic Loop

## Task Description

Implement Phase 3 of the procurement assistant: dynamic fan-out via LangGraph `Send` API, the Critic evaluator-optimizer loop, targeted worker re-dispatch on revision, and schema enhancements for freshness metadata. Covers delivery checklist items 3.1–3.6.

## Objective

After Phase 3, the system dispatches subtasks to workers in parallel via `Send`, evaluates the aggregated response with a Critic agent (Freshness / Completeness / Structure dimensions), and re-runs only flagged workers on `revise` verdict — cycling up to `CRITIC_MAX_RETRIES` before escalating. Planner can now emit multi-topic subtask lists.

## Problem Statement

Phase 2 left a single-topic graph: one worker, no parallel execution, no quality control loop. The architecture requires orchestrator-workers fan-out and evaluator-optimizer cycle. Without them the system cannot handle multi-domain queries and cannot self-correct low-quality or stale answers.

## Solution Approach

1. **Schemas first** — extend `CritiqueResult` with typed score fields and `RevisionRequest`; add `Source.metadata` for date.
2. **Planner multi-topic** — lift the single-subtask constraint from the prompt; add few-shot examples showing 2–3 subtask plans.
3. **Fan-out** — two no-op nodes (`fan_out_dispatcher`, `targeted_redispatcher`) whose only purpose is to be the source of conditional edges returning `list[Send]`. Workers receive the Send input dict, not full state.
4. **Aggregator** — `aggregate_responses_node` deduplicates `worker_responses` by keeping last-per-topic (reducer accumulates all rounds), then writes `aggregated_response`.
5. **Critic** — `agents/critic.py` calls LLM with `with_structured_output(CritiqueResult)`; no tools. `prompts/critic.md` defines three scoring dimensions.
6. **Critic loop** — `critic_node` → `route_after_critic` (approve / revise / escalate-on-max-retries) → `targeted_redispatcher` → targeted workers → `aggregate_responses_node` (cycle).
7. **Revision feedback** — all `invoke_X` functions accept `revision_feedback: str | None = None`; prepended to query when present.
8. **RAG tool date line** — `tools/rag.py` adds a `Дата:` line so Critic can assess freshness.

### Architecture Decisions

- **Affected graph nodes**: Planner (prompt only), all three workers (revision_feedback param), new `fan_out_dispatcher`, `aggregate_responses_node`, `critic_node`, `targeted_redispatcher`, `escalation_stub_node` (from Phase 2 — unchanged), `final_response_node`.
- **Schemas**: `RevisionRequest` new model; `CritiqueResult` refactored (typed scores, `list[RevisionRequest]`); `Source.metadata` added; `GraphState` no new fields (existing `retry_count`, `critic_history`, `aggregated_response`, `worker_responses` reducer suffice).
- **RAG collection(s)**: unchanged; `tools/rag.py` format change only (add date line).
- **External calls**: no new external calls; Critic is a pure LLM call.
- **Sessions / persistence**: no change to checkpoint format.
- **Prompt source**: new `prompts/critic.md` (Langfuse: create `critic` prompt); update `prompts/planner.md` (Langfuse: update `planner` prompt).

## Relevant Files

- `schemas.py` — add `RevisionRequest`, refactor `CritiqueResult`, add `Source.metadata`
- `agents/planner.py` — no Python change; prompt controls subtask count
- `prompts/planner.md` — remove single-subtask instruction, add multi-topic few-shot examples
- `agents/lawyer.py` — add `revision_feedback` param to `invoke_lawyer`, update `lawyer_node` for Send input
- `agents/common_support.py` — same revision_feedback pattern
- `agents/technical_support.py` — same revision_feedback pattern
- `tools/rag.py` — add `Дата:` line to formatted chunk output
- `supervisor.py` — full graph rewrite: fan-out, aggregator, critic loop, targeted redispatch, cycles
- `final_response.py` — minor update: reads `aggregated_response` from state (unchanged if already correct)
- `config.py` — verify `critic_max_retries` and `planner_max_subtasks` present (no change needed per Phase 2)

### New Files

- `agents/critic.py` — Critic agent using `with_structured_output(CritiqueResult)`
- `prompts/critic.md` — system prompt with Freshness / Completeness / Structure rubric
- `tests/test_critic.py` — unit tests for `invoke_critic` and `critic_node`
- `tests/test_aggregator.py` — unit tests for `aggregate_responses_node` deduplication
- `tests/test_fanout_routing.py` — unit tests for `fan_out_send` and `targeted_redispatch_send`

## Step by Step Tasks

### 1. Schemas (schemas.py)

- [ ] **Add `RevisionRequest` model** — new Pydantic model capturing which worker needs to redo work and why:
  ```python
  class RevisionRequest(BaseModel):
      topic: Literal["legal", "procurement_general", "technical_system"]
      request: str
      severity: Literal["minor", "major"]
  ```
  - Status:
  - Comments:

- [ ] **Refactor `CritiqueResult`** — replace `dimensions: dict` with explicit typed score fields; replace `list[dict]` with `list[RevisionRequest]`; remove `"escalate"` from `verdict` (escalation is triggered by `retry_count` in graph router, not by Critic); add validator:
  ```python
  class CritiqueResult(BaseModel):
      verdict: Literal["approve", "revise"]
      freshness_score: float = Field(ge=0.0, le=1.0)
      completeness_score: float = Field(ge=0.0, le=1.0)
      structure_score: float = Field(ge=0.0, le=1.0)
      gaps: list[str] = Field(default_factory=list)
      revision_requests: list[RevisionRequest] = Field(default_factory=list)
      summary: str = ""

      @model_validator(mode="after")
      def validate_revisions(self) -> "CritiqueResult":
          if self.verdict == "revise" and not self.revision_requests:
              raise ValueError("revise verdict requires at least one revision_request")
          return self
  ```
  - Status:
  - Comments:

- [ ] **Add `Source.metadata`** — enables workers to pass date fields through to Critic:
  ```python
  class Source(BaseModel):
      title: str
      url: str | None = None
      doc_id: str
      metadata: dict = Field(default_factory=dict)  # version_date, date_published
  ```
  - Status:
  - Comments:

- [ ] **Verify `GraphState` sufficiency** — confirm existing fields cover Phase 3 needs. No new fields required: `worker_responses: Annotated[list[WorkerResponse], operator.add]` accumulates across rounds; `retry_count: int` tracks critic cycles; `critic_history: list[CritiqueResult]` stores all verdicts; `aggregated_response: str | None` is written by aggregator.
  - Status:
  - Comments:

### 2. Planner Multi-topic (prompts/planner.md)

- [ ] **Remove single-subtask constraint** — delete any instruction that limits subtasks to 1. Set instruction: the planner may emit 1 to `{planner_max_subtasks}` subtasks; use multiple topics only when the query genuinely spans domains.
  - Status:
  - Comments:

- [ ] **Add few-shot examples** — include at least two examples: one single-topic query (legal) producing 1 subtask; one multi-domain query producing 2–3 subtasks across different topics. Format must match `ResearchPlan` JSON schema exactly.
  - Status:
  - Comments:

- [ ] **Update Langfuse** — push updated `planner` prompt to Langfuse Prompt Management; version bump comment in `prompts/planner.md`.
  - Status:
  - Comments:

### 3. Worker Node Signatures for Send Input

- [ ] **Redesign `lawyer_node`** — Phase 3 workers receive a Send input dict `{"subtask": SubTask, "revision_feedback": str | None}`, NOT full `GraphState`. Update signature:
  ```python
  def lawyer_node(state: dict) -> dict:
      subtask: SubTask = state["subtask"]
      feedback: str | None = state.get("revision_feedback")
      return {"worker_responses": [invoke_lawyer(subtask.query, revision_feedback=feedback)]}
  ```
  - Status:
  - Comments:

- [ ] **Update `invoke_lawyer`** — add `revision_feedback: str | None = None` parameter; prepend feedback to query when present:
  ```python
  def invoke_lawyer(query: str, revision_feedback: str | None = None) -> WorkerResponse:
      if revision_feedback:
          query = f"[REVISION REQUEST]: {revision_feedback}\n\n[ORIGINAL QUERY]: {query}"
      result = get_lawyer_agent().invoke({"messages": [HumanMessage(content=query)]})
      return result["structured_response"]
  ```
  - Status:
  - Comments:

- [ ] **Apply same pattern to `common_support_node` / `invoke_common_support`** — in `agents/common_support.py`.
  - Status:
  - Comments:

- [ ] **Apply same pattern to `technical_support_node` / `invoke_technical_support`** — in `agents/technical_support.py`.
  - Status:
  - Comments:

### 4. Fan-out Dispatcher (supervisor.py)

- [ ] **Implement `fan_out_send` conditional edge** — returns `list[Send]`, one per subtask:
  ```python
  from langgraph.types import Send

  _TOPIC_NODE = {
      "legal": "lawyer_node",
      "procurement_general": "common_support_node",
      "technical_system": "technical_support_node",
  }

  def fan_out_send(state: GraphState) -> list[Send]:
      return [
          Send(_TOPIC_NODE[st.topic], {"subtask": st, "revision_feedback": None})
          for st in state["plan"].subtasks
      ]
  ```
  - Status:
  - Comments:

- [ ] **Add `fan_out_dispatcher` no-op node** — empty function; exists only as the anchor for `add_conditional_edges`:
  ```python
  def fan_out_dispatcher(state: GraphState) -> dict:
      return {}
  ```
  - Status:
  - Comments:

- [ ] **Wire in graph** — add node + conditional edge:
  ```python
  graph.add_node("fan_out_dispatcher", fan_out_dispatcher)
  graph.add_conditional_edges(
      "fan_out_dispatcher",
      fan_out_send,
      ["lawyer_node", "common_support_node", "technical_support_node"],
  )
  ```
  - Status:
  - Comments:

### 5. Aggregator Node (supervisor.py)

- [ ] **Implement `aggregate_responses_node`** — deduplicates `worker_responses` by keeping the last response per topic (handles multiple rounds without losing earlier data for unapproved topics):
  ```python
  def aggregate_responses_node(state: GraphState) -> dict:
      deduped: dict[str, WorkerResponse] = {}
      for resp in state["worker_responses"]:
          deduped[resp.topic] = resp  # last write wins per topic

      topic_order = ["legal", "procurement_general", "technical_system"]
      ordered = [deduped[t] for t in topic_order if t in deduped]

      sections: list[str] = []
      for resp in ordered:
          if resp.found and resp.answer:
              sections.append(resp.answer)

      aggregated = "\n\n---\n\n".join(sections) if sections else ""
      return {"aggregated_response": aggregated}
  ```
  - Status:
  - Comments:

- [ ] **Wire aggregator into graph** — all three worker nodes converge here:
  ```python
  graph.add_node("aggregate_responses_node", aggregate_responses_node)
  for worker in ["lawyer_node", "common_support_node", "technical_support_node"]:
      graph.add_edge(worker, "aggregate_responses_node")
  ```
  - Status:
  - Comments:

### 6. Critic Agent (agents/critic.py + prompts/critic.md)

- [ ] **Create `prompts/critic.md`** — system prompt with three scoring dimensions:
  - **Freshness** (0–1): check `Дата:` lines in cited sources; flag answers citing laws/articles older than threshold.
  - **Completeness** (0–1): verify each subtask in the plan has a corresponding answer section; flag missing topics.
  - **Structure** (0–1): answer is in Ukrainian, clearly organized, sources cited, no hallucinated article numbers.
  - Instruct: return `verdict="revise"` if any score < 0.6; list `revision_requests` for each flagged topic with specific `request` text.
  - Status:
  - Comments:

- [ ] **Create `agents/critic.py`** — no tools; pure structured output:
  ```python
  """Critic agent: evaluates aggregated response quality across Freshness/Completeness/Structure."""

  from __future__ import annotations

  from pathlib import Path

  from langchain_anthropic import ChatAnthropic
  from langchain_core.language_models import BaseChatModel
  from langchain_core.messages import HumanMessage, SystemMessage
  from langchain_openai import ChatOpenAI

  from config import settings
  from schemas import CritiqueResult, GraphState, ResearchPlan, WorkerResponse

  _PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


  def _get_llm() -> BaseChatModel:
      if settings.llm_provider == "openai":
          assert settings.openai_api_key
          return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key.get_secret_value())
      assert settings.anthropic_api_key
      return ChatAnthropic(model=settings.llm_model, api_key=settings.anthropic_api_key.get_secret_value())


  def _load_system_prompt() -> str:
      return (_PROMPTS_DIR / "critic.md").read_text(encoding="utf-8")


  def invoke_critic(
      aggregated_response: str,
      plan: ResearchPlan,
      worker_responses: list[WorkerResponse],
  ) -> CritiqueResult:
      llm = _get_llm().with_structured_output(CritiqueResult)
      system = _load_system_prompt()
      human = (
          f"## Оригінальний запит\n{plan.original_query}\n\n"
          f"## План дослідження\n{plan.model_dump_json(indent=2)}\n\n"
          f"## Відповіді агентів (з джерелами)\n{aggregated_response}\n\n"
          f"## Метадані агентів\n"
          + "\n".join(
              f"- {r.topic}: found={r.found}, confidence={r.confidence}"
              for r in worker_responses
          )
      )
      result = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
      return result


  def critic_node(state: GraphState) -> dict:
      critique = invoke_critic(
          aggregated_response=state["aggregated_response"] or "",
          plan=state["plan"],
          worker_responses=state["worker_responses"],
      )
      return {
          "critic_history": state["critic_history"] + [critique],
          "retry_count": state["retry_count"] + 1,
      }
  ```
  - Status:
  - Comments:

- [ ] **Push `critic` prompt to Langfuse** — create new `critic` prompt entry; note version in `prompts/critic.md` header comment.
  - Status:
  - Comments:

### 7. Critic Loop in Graph (supervisor.py)

- [ ] **Implement `route_after_critic`** — returns string route; escalation triggered by exhausted retries, NOT by Critic verdict:
  ```python
  def route_after_critic(state: GraphState) -> str:
      last_critique = state["critic_history"][-1]
      if last_critique.verdict == "approve":
          return "final_response_node"
      if state["retry_count"] >= settings.critic_max_retries:
          return "escalation_stub_node"
      return "targeted_redispatcher"
  ```
  - Status:
  - Comments:

- [ ] **Implement `targeted_redispatch_send`** — returns `list[Send]`, one per revision request; attaches `revision_feedback` from the specific `RevisionRequest`:
  ```python
  def targeted_redispatch_send(state: GraphState) -> list[Send]:
      last_critique = state["critic_history"][-1]
      sends: list[Send] = []
      for rev_req in last_critique.revision_requests:
          subtask = next(
              (st for st in state["plan"].subtasks if st.topic == rev_req.topic),
              None,
          )
          if subtask is None:
              continue
          sends.append(
              Send(
                  _TOPIC_NODE[rev_req.topic],
                  {"subtask": subtask, "revision_feedback": rev_req.request},
              )
          )
      return sends
  ```
  - Status:
  - Comments:

- [ ] **Add `targeted_redispatcher` no-op node** — mirrors `fan_out_dispatcher`:
  ```python
  def targeted_redispatcher(state: GraphState) -> dict:
      return {}
  ```
  - Status:
  - Comments:

- [ ] **Wire critic loop in graph**:
  ```python
  graph.add_node("critic_node", critic_node)
  graph.add_node("targeted_redispatcher", targeted_redispatcher)

  graph.add_edge("aggregate_responses_node", "critic_node")

  graph.add_conditional_edges(
      "critic_node",
      route_after_critic,
      {
          "final_response_node": "final_response_node",
          "escalation_stub_node": "escalation_stub_node",
          "targeted_redispatcher": "targeted_redispatcher",
      },
  )

  graph.add_conditional_edges(
      "targeted_redispatcher",
      targeted_redispatch_send,
      ["lawyer_node", "common_support_node", "technical_support_node"],
  )
  ```
  This creates a deliberate cycle: `targeted_redispatcher → workers → aggregate_responses_node → critic_node → targeted_redispatcher`.
  - Status:
  - Comments:

- [ ] **Verify full `supervisor.py` graph edges** — from Phase 2, `planner_node → route_after_planner → {off_topic_node, escalation_stub_node, fan_out_dispatcher}`. Extend to include `fan_out_dispatcher → fan_out_send → workers`. Full edge list in order:
  1. START → planner_node
  2. planner_node → route_after_planner → {off_topic / escalation_stub / fan_out_dispatcher}
  3. fan_out_dispatcher → fan_out_send → [workers]
  4. workers → aggregate_responses_node
  5. aggregate_responses_node → critic_node
  6. critic_node → route_after_critic → {final_response_node / escalation_stub_node / targeted_redispatcher}
  7. targeted_redispatcher → targeted_redispatch_send → [workers]
  8. off_topic_node → END; escalation_stub_node → END; final_response_node → END
  - Status:
  - Comments:

### 8. RAG Tool Date Line (tools/rag.py)

- [ ] **Add `Дата:` line to chunk formatter** — helps Critic assess freshness without parsing metadata directly:
  ```python
  date_str = meta.get("version_date") or meta.get("date_published") or "невідомо"
  chunk_text = f"---\n{breadcrumb}\n{text}\nДжерело: {source}\nДата: {date_str}\n"
  ```
  Both `version_date` (laws) and `date_published` (articles) must be handled; fall back to `"невідомо"` when absent.
  - Status:
  - Comments:

### 9. Tests

- [ ] **`tests/test_aggregator.py`** — test `aggregate_responses_node`:
  - Single topic: returns correct `aggregated_response`.
  - Multi-round accumulation: three responses in round 1, two in round 2 (same topics) — deduplication keeps last; third topic from round 1 survives.
  - All `found=False`: `aggregated_response` is empty string.
  - Status:
  - Comments:

- [ ] **`tests/test_fanout_routing.py`** — test Send routing:
  - `fan_out_send` with 1-subtask plan → returns 1 `Send` targeting correct node.
  - `fan_out_send` with 3-subtask plan → returns 3 `Send`s, each targeting the correct topic node.
  - `targeted_redispatch_send` with 2 revision requests → returns 2 `Send`s with `revision_feedback` populated.
  - `targeted_redispatch_send` with revision request for unknown topic (not in plan) → skips it, returns 0 `Send`s.
  - Status:
  - Comments:

- [ ] **`tests/test_critic.py`** — test Critic with mocked LLM:
  - `invoke_critic` returns a valid `CritiqueResult` (mock `with_structured_output` chain).
  - `critique_result.verdict == "revise"` with empty `revision_requests` raises `ValidationError`.
  - `route_after_critic`: approve → `"final_response_node"`; revise + retries < max → `"targeted_redispatcher"`; revise + retries >= max → `"escalation_stub_node"`.
  - Status:
  - Comments:

- [ ] **`tests/test_schemas.py`** — test new schema validators:
  - `RevisionRequest` fields and Literal constraints.
  - `CritiqueResult` validator: revise without revision_requests raises `ValueError`.
  - `Source.metadata` defaults to empty dict.
  - Status:
  - Comments:

- [ ] **Update `tests/conftest.py`** — add fixtures for multi-topic `ResearchPlan`, multi-round `worker_responses` list, and sample `CritiqueResult` objects (both verdicts).
  - Status:
  - Comments:

## Testing Strategy

**Unit tests** (fast, no LLM calls):
- Mock `_get_llm().with_structured_output(CritiqueResult)` to return deterministic `CritiqueResult` fixtures.
- Test graph routing functions (`route_after_critic`, `fan_out_send`, `targeted_redispatch_send`) directly — they are pure functions over `GraphState`.
- Test aggregator deduplication with hand-crafted multi-round `worker_responses` lists.
- Test schema validators for `CritiqueResult` and `RevisionRequest`.

**Integration smoke test** (optional, requires running Qdrant + LLM):
```bash
python -c "
from supervisor import build_graph
from schemas import GraphState
g = build_graph()
result = g.invoke({
    'user_message': 'Які строки розгляду скарги до АМКУ та вимоги до процедури закупівлі за статтею 18?',
    'session_id': 'test-phase3', 'user_id': 'tester',
    'plan': None, 'worker_responses': [], 'critic_history': [],
    'retry_count': 0, 'aggregated_response': None, 'escalated': False, 'final_response': None,
})
assert result['final_response'], 'Expected final response'
print('PASS')
"
```

**DeepEval LLM eval** (`tests/eval/`):
- Groundedness: all claims in `final_response` traceable to retrieved chunks.
- Completeness: all subtasks in plan covered in final response.
- Critic accuracy GEval: does `critique.summary` correctly identify gaps visible in the response?

## Acceptance Criteria

1. Multi-topic query (e.g. legal + technical) produces two subtasks in `ResearchPlan`; `fan_out_send` dispatches two parallel `Send`s.
2. `aggregate_responses_node` correctly deduplicates multi-round `worker_responses`; field `aggregated_response` is non-empty when at least one worker returns `found=True`.
3. `critic_node` runs and returns a valid `CritiqueResult` with numeric scores for all three dimensions.
4. On `verdict="revise"`, only workers listed in `revision_requests` are re-dispatched; workers not flagged are NOT re-run.
5. After `CRITIC_MAX_RETRIES` revise cycles, graph routes to `escalation_stub_node` rather than looping.
6. On `verdict="approve"`, graph routes to `final_response_node` and returns `final_response` in state.
7. All three worker `invoke_X` functions accept `revision_feedback` and prepend it to the query string when non-None.
8. RAG tool output includes `Дата:` line for each chunk; falls back to `"невідомо"` when date fields absent.
9. All unit tests in `tests/test_aggregator.py`, `tests/test_fanout_routing.py`, `tests/test_critic.py`, `tests/test_schemas.py` pass.
10. No syntax errors across modified modules.

## Validation Commands

```bash
# Syntax check all modified files
python -m py_compile schemas.py tools/rag.py agents/critic.py agents/lawyer.py \
    agents/common_support.py agents/technical_support.py agents/planner.py \
    supervisor.py final_response.py

# Graph imports cleanly and has expected node set
python -c "
from supervisor import build_graph
g = build_graph()
nodes = set(g.nodes)
required = {'planner_node','fan_out_dispatcher','lawyer_node','common_support_node',
            'technical_support_node','aggregate_responses_node','critic_node',
            'targeted_redispatcher','final_response_node','escalation_stub_node'}
missing = required - nodes
assert not missing, f'Missing nodes: {missing}'
print('Graph OK:', sorted(nodes))
"

# Unit tests
pytest tests/test_aggregator.py tests/test_fanout_routing.py tests/test_critic.py tests/test_schemas.py -v

# Full test suite
pytest tests/ -q

# DeepEval (when eval/ tests exist)
deepeval test run tests/eval/
```

## Notes

- The cycle (`targeted_redispatcher → workers → aggregate_responses_node → critic_node → targeted_redispatcher`) is intentional and supported by LangGraph. The `retry_count` field in `GraphState` is the loop termination guard; it must be incremented in `critic_node` before routing.
- `CritiqueResult.verdict` no longer includes `"escalate"` — this is intentional. The Critic scores quality; the graph router decides when to escalate. This keeps the Critic's concerns pure and prevents the LLM from bypassing the retry budget.
- `operator.add` on `worker_responses` accumulates responses from ALL rounds. The aggregator must deduplicate — otherwise round 2 responses for topic X would appear twice in `aggregated_response`.
- `fan_out_send` and `targeted_redispatch_send` must list all possible target node names as the third argument to `add_conditional_edges`. LangGraph validates this at compile time.
- When `revision_requests` refers to a topic not in `plan.subtasks` (e.g., Critic hallucinates a topic), `targeted_redispatch_send` silently skips it. This is defensive — don't raise, just ignore unknown topics.
- The Critic prompt should explicitly state that `revision_requests` must only contain topics present in the plan subtasks, to minimize the skip case above.
- New library dependency: none. All components use existing stack (`langchain_anthropic`, `langchain_openai`, `langgraph`, `pydantic`).
- Langfuse: create `critic` prompt at the same label/version convention as existing prompts. Record the version string in a comment at the top of `prompts/critic.md` after creation.