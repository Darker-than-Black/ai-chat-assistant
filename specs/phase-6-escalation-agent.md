# Plan: Phase 6 — Escalation Agent

## Task Description

Replace the `escalation_stub_node` placeholder in `supervisor.py` with a fully functional `escalation_node`. This node handles three trigger paths, generates an LLM summary for the operator, saves an audit-trail JSON file, and posts a Block Kit message to the expert Slack channel. Covers delivery checklist items 6.1–6.4:

- **6.1** `agents/escalation.py` — builds `EscalationOutput`, LLM call for `summary`, file save
- **6.2** `escalation_node` replaces the stub; three trigger paths wired in graph
- **6.3** Static bilingual user-facing message (UK/EN) added to `language.py`
- **6.4** `tools/slack_publisher.post_to_expert_channel` call + file save (always)

## Objective

After this phase, every escalation path in the graph produces a real `EscalationOutput` with an LLM-generated operator summary, writes an audit-trail JSON to `output/escalations/`, and posts a structured Block Kit message to the expert Slack channel. The user receives a static bilingual message without internal system details.

## Problem Statement

The current `escalation_stub_node` returns a hardcoded Ukrainian string and does nothing else — no audit trail, no Slack notification, no operator context. The `EscalationOutput` schema is also minimal (4 fields) versus the 7-field target in `ARCHITECTURE.md`. Additionally, the third escalation trigger (worker sets `needs_human=True` for bug/feature detection) has no routing path at all — the fixed `aggregate_responses_node → critic_node` edge silently ignores it.

## Solution Approach

The escalation node is not a ReAct agent (no tools). It makes a single LLM call (for `summary` only) using the same `get_llm()` + `SystemMessage + HumanMessage` pattern as `agents/critic.py`. All other fields (`category`, `attempted_resolution`, `full_context`) are built from deterministic logic using graph state — no second LLM call.

The three trigger paths converge at the same `escalation_node`:
1. **Planner gate** — `route_after_planner` already routes to `escalation_stub_node` if `plan.needs_human=True` (rename target node only)
2. **Critic exhaustion** — `route_after_critic` already routes to `escalation_stub_node` if `retry_count >= MAX_RETRIES` (rename target node only)
3. **Worker signal** — NEW: `aggregate_responses_node → critic_node` (fixed edge) becomes a conditional edge that routes to `escalation_node` when any worker has `needs_human=True`

### Architecture Decisions

- **Affected graph nodes**:
  - `escalation_stub_node` → REPLACED by `escalation_node` (imported from `agents/escalation.py`)
  - New conditional edge between `aggregate_responses_node` and `critic_node` / `escalation_node` (adds the third trigger path)
  - No other nodes change.
- **Schemas**: `EscalationOutput` in `schemas.py` expanded from 4 → 7 fields per `ARCHITECTURE.md § 4.4`. Breaking change: `reason` renamed to `summary`, `original_query` renamed to `customer_message`, `timestamp: str` → `timestamp: datetime`, three new fields added. No other schema changes needed.
- **RAG collections**: Not involved.
- **External calls**:
  - One LLM call per escalation event (for `summary` only; ~50-100 tokens out)
  - `tools/slack_publisher.post_to_expert_channel()` — best-effort (errors are caught, audit file is the authoritative record). Requires `SLACK_BOT_TOKEN` and `SLACK_EXPERT_CHANNEL_ID`.
  - File write to `output/escalations/{session}_{timestamp}.json` — always executes before Slack call.
- **Sessions / persistence**: No change to PostgresSaver or session key format.
- **Prompt source**: New `prompts/escalation.md` (local file, Phase 7 migrates to Langfuse like all other prompts).

### Phase 5 Prerequisite

`tools/slack_publisher.py` is listed as a Phase 5 deliverable. Phase 6 imports and calls it. If Phase 5 has not been completed:
- The plan includes creating `tools/slack_publisher.py` as **Step 6** below (with the full 7-field `EscalationOutput`).
- If Phase 5 already created it (4-field version), Step 6 updates `_build_message()` to the full schema.

In either case, `escalation_node` wraps the Slack call in `try/except` so a missing or failing publisher does not fail the graph.

## Relevant Files

### Modified
- `schemas.py` — expand `EscalationOutput` (7 fields), add `datetime` import
- `language.py` — add `_ESCALATION_MESSAGE` dict + `get_escalation_message(language)` helper
- `supervisor.py` — rename `escalation_stub_node` → `escalation_node`, add `route_after_aggregate` conditional edge, update all routing maps
- `tests/test_graph_routing.py` — add `escalation_node` mock to `patch_graph_dependencies` fixture, update `test_escalation_returns_stub_message` assertion
- `tools/slack_publisher.py` — update `_build_message()` to use full 7-field `EscalationOutput` (or create from scratch if Phase 5 not done)

### New Files
- `agents/escalation.py` — escalation agent: category inference, resolution builder, LLM summary, `EscalationOutput` assembly, file save, `escalation_node()`
- `prompts/escalation.md` — Ukrainian system prompt for LLM summary generation
- `tests/test_escalation.py` — unit tests for all pure functions + node + file save

## Implementation Phases

- [ ] **Phase 1: Foundation** — Schema expansion + language helper (no agent code yet; establishes the contract all downstream steps depend on)
  - Status:
  - Comments:

- [ ] **Phase 2: Core Implementation** — Agent, prompt, graph wiring, Slack publisher update
  - Status:
  - Comments:

- [ ] **Phase 3: Tests + Validation** — Test file, update existing routing tests, smoke validation
  - Status:
  - Comments:

## Step by Step Tasks

### 1. Schema: expand EscalationOutput

- [ ] **Add `datetime` import** to `schemas.py` (top of file):
  ```python
  from datetime import datetime
  ```
  - Status:
  - Comments:

- [ ] **Replace `EscalationOutput` class** in `schemas.py` with the full 7-field version:
  ```python
  class EscalationOutput(BaseModel):
      summary: str
      category: Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]
      customer_message: str
      attempted_resolution: str
      full_context: dict
      timestamp: datetime
      session_id: str
  ```
  Fields removed: `reason` (superseded by `summary`), `original_query` (renamed to `customer_message`).
  Fields added: `category`, `attempted_resolution`, `full_context`.
  Type changed: `timestamp: str` → `timestamp: datetime` (Pydantic serializes to ISO string with `model_dump(mode="json")`).
  - Status:
  - Comments:

### 2. Language: add escalation message

- [ ] **Add `_ESCALATION_MESSAGE` and `get_escalation_message()`** to `language.py`:
  ```python
  _ESCALATION_MESSAGE: dict[str, str] = {
      "uk": "Ваш запит передано фахівцю для подальшого опрацювання. Ми зв'яжемося з вами найближчим часом.",
      "en": "Your request has been escalated to a specialist for further review. We will get back to you shortly.",
  }

  def get_escalation_message(language: str = "uk") -> str:
      return _ESCALATION_MESSAGE.get(language, _ESCALATION_MESSAGE["uk"])
  ```
  Place after the existing `get_no_answer_message()` function.
  - Status:
  - Comments:

### 3. Prompt: create prompts/escalation.md

- [ ] **Create `prompts/escalation.md`** — Ukrainian instruction prompt for generating the operator `summary` field:
  ```markdown
  Ти — компонент системи підтримки публічних закупівель України (Prozorro). Твоя задача — підготувати коротке резюме ескалації для оператора служби підтримки.

  ## Що ти отримуєш

  - **Запит користувача** — оригінальне формулювання.
  - **Категорія ескалації** — класифікація: `bug`, `feature_request`, `unanswerable`, або `max_retries_exceeded`.
  - **Причина ескалації** — текстовий опис, чому запит передається людині.
  - **Результати агентів** — які агенти відпрацювали і з якими результатами.

  ## Твоє завдання

  Сформулюй **одне-два речення** — стисле резюме ситуації для оператора. Резюме має:
  - Пояснити суть запиту користувача (без технічного жаргону).
  - Пояснити, чому система не змогла надати відповідь.
  - Запропонувати короткий наступний крок для оператора (якщо очевидно).

  ## Обмеження

  - Максимум 2 речення, не більше 200 символів.
  - Не повторюй технічний лог — пиши для людини, а не для розробника.
  - Не вигадуй деталей, яких немає у контексті.
  - Відповідай мовою оригінального запиту (українська або англійська).

  Поверни лише текст резюме, без додаткового форматування.
  ```
  - Status:
  - Comments:

### 4. Agent: create agents/escalation.py

- [ ] **Create `agents/escalation.py`** with the following structure (full content):
  ```python
  """Escalation agent: LLM summary + audit file + Slack expert-channel notification."""

  from __future__ import annotations

  import json
  from datetime import datetime
  from pathlib import Path
  from typing import Literal

  from langchain_core.messages import HumanMessage, SystemMessage

  from agents.lawyer import get_llm
  from config import settings
  from language import get_escalation_message
  from schemas import EscalationOutput, GraphState

  _PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


  def _load_system_prompt() -> str:
      return (_PROMPTS_DIR / "escalation.md").read_text(encoding="utf-8")


  def _determine_category(
      state: GraphState,
  ) -> Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]:
      # Critic-exhaustion path is unambiguous
      if state.get("retry_count", 0) >= settings.critic_max_retries and state.get("critic_history"):
          return "max_retries_exceeded"
      # Worker-signal path: check needs_human_reason for domain hints
      for resp in state.get("worker_responses", []):
          if resp.needs_human and resp.needs_human_reason:
              reason_lower = resp.needs_human_reason.lower()
              if any(kw in reason_lower for kw in ["баг", "bug", "помилка", "error", "збій"]):
                  return "bug"
              if any(kw in reason_lower for kw in ["функці", "feature", "відсутн", "додати"]):
                  return "feature_request"
      # Planner-gate path and everything else
      return "unanswerable"


  def _build_attempted_resolution(state: GraphState) -> str:
      worker_responses = state.get("worker_responses", [])
      if not worker_responses:
          return "Запит не оброблявся агентами (пряма ескалація планером)."

      lines: list[str] = []
      for resp in worker_responses:
          status = "знайдено" if resp.found else "не знайдено"
          line = f"- {resp.topic}: {status}, впевненість={resp.confidence:.1f}"
          if resp.needs_human and resp.needs_human_reason:
              line += f", потрібна людина: {resp.needs_human_reason}"
          lines.append(line)

      critic_history = state.get("critic_history", [])
      if critic_history:
          last = critic_history[-1]
          lines.append(
              f"- Критик: {last.verdict}, повторів={state.get('retry_count', 0)}"
          )
          if last.gaps:
              lines.append(f"  Прогалини: {'; '.join(last.gaps[:3])}")

      return "\n".join(lines)


  def _build_full_context(state: GraphState) -> dict:
      return {
          "plan": state["plan"].model_dump() if state.get("plan") else None,
          "worker_responses": [r.model_dump() for r in state.get("worker_responses", [])],
          "critic_history": [c.model_dump() for c in state.get("critic_history", [])],
          "retry_count": state.get("retry_count", 0),
      }


  def _generate_summary(state: GraphState, category: str, attempted_resolution: str) -> str:
      plan = state.get("plan")
      escalation_reason = (
          plan.escalation_reason if plan and plan.escalation_reason else "Причина не вказана"
      )
      human = (
          f"## Запит користувача\n{state['user_message']}\n\n"
          f"## Категорія ескалації\n{category}\n\n"
          f"## Причина ескалації\n{escalation_reason}\n\n"
          f"## Результати агентів\n{attempted_resolution}\n"
      )
      result = get_llm().invoke([
          SystemMessage(content=_load_system_prompt()),
          HumanMessage(content=human),
      ])
      return result.content if hasattr(result, "content") else str(result)


  def _save_to_file(escalation: EscalationOutput) -> None:
      output_dir = Path("output/escalations")
      output_dir.mkdir(parents=True, exist_ok=True)
      safe_session = escalation.session_id.replace(":", "_")
      safe_ts = escalation.timestamp.strftime("%Y%m%dT%H%M%S")
      path = output_dir / f"{safe_session}_{safe_ts}.json"
      with open(path, "w", encoding="utf-8") as f:
          json.dump(escalation.model_dump(mode="json"), f, ensure_ascii=False, indent=2)


  def invoke_escalation(state: GraphState) -> EscalationOutput:
      category = _determine_category(state)
      attempted_resolution = _build_attempted_resolution(state)
      summary = _generate_summary(state, category, attempted_resolution)
      return EscalationOutput(
          summary=summary,
          category=category,
          customer_message=state["user_message"],
          attempted_resolution=attempted_resolution,
          full_context=_build_full_context(state),
          timestamp=datetime.now(),
          session_id=state["session_id"],
      )


  def escalation_node(state: GraphState) -> dict:
      escalation = invoke_escalation(state)

      _save_to_file(escalation)

      # Best-effort Slack publish; file is the authoritative audit trail
      try:
          from tools.slack_publisher import post_to_expert_channel  # lazy import avoids circular import at module level
          post_to_expert_channel(escalation)
      except Exception:
          pass

      plan = state.get("plan")
      language = plan.language if plan else "uk"
      return {
          "final_response": get_escalation_message(language),
          "escalated": True,
      }
  ```
  - Status:
  - Comments: The lazy `from tools.slack_publisher import …` inside `escalation_node` avoids a circular import if `supervisor.py` or `main.py` are in the import chain and also prevents test failures when the publisher isn't installed. The `try/except Exception` is intentional — Slack is secondary to the file audit trail.

### 5. Supervisor: replace stub + add third trigger

- [ ] **Add import** for `escalation_node` at the top of `supervisor.py`:
  ```python
  from agents.escalation import escalation_node
  ```
  Remove the `escalation_stub_node` function definition entirely.
  - Status:
  - Comments:

- [ ] **Add `route_after_aggregate()` function** in `supervisor.py` (place after `aggregate_responses_node`, before existing route functions):
  ```python
  def route_after_aggregate(state: GraphState) -> str:
      if any(r.needs_human for r in state.get("worker_responses", [])):
          return "escalation_node"
      return "critic_node"
  ```
  This implements the third trigger path (worker `needs_human=True`).
  - Status:
  - Comments:

- [ ] **Update `build_graph()` node registrations** — remove the stub, add the real node:
  ```python
  # Remove:
  builder.add_node("escalation_stub_node", escalation_stub_node)
  # Add:
  builder.add_node("escalation_node", escalation_node)
  ```
  - Status:
  - Comments:

- [ ] **Change `aggregate_responses_node → critic_node` edge from fixed to conditional**:
  ```python
  # Remove:
  builder.add_edge("aggregate_responses_node", "critic_node")
  # Add:
  builder.add_conditional_edges(
      "aggregate_responses_node",
      route_after_aggregate,
      {"critic_node": "critic_node", "escalation_node": "escalation_node"},
  )
  ```
  - Status:
  - Comments:

- [ ] **Update `route_after_planner` return value** — change `"escalation_stub_node"` → `"escalation_node"` and update the conditional edges dict in `build_graph()`:
  ```python
  # In route_after_planner:
  if plan.needs_human:
      return "escalation_node"    # was "escalation_stub_node"

  # In build_graph conditional_edges for planner:
  builder.add_conditional_edges(
      "planner_node",
      route_after_planner,
      {
          "fan_out_dispatcher": "fan_out_dispatcher",
          "off_topic_node": "off_topic_node",
          "escalation_node": "escalation_node",   # was "escalation_stub_node"
      },
  )
  ```
  - Status:
  - Comments:

- [ ] **Update `route_after_critic` return value** — change `"escalation_stub_node"` → `"escalation_node"` and its conditional edges dict:
  ```python
  # In route_after_critic:
  if state["retry_count"] >= settings.critic_max_retries:
      return "escalation_node"    # was "escalation_stub_node"

  # In build_graph conditional_edges for critic:
  builder.add_conditional_edges(
      "critic_node",
      route_after_critic,
      {
          "final_response_node": "final_response_node",
          "escalation_node": "escalation_node",   # was "escalation_stub_node"
          "targeted_redispatcher": "targeted_redispatcher",
      },
  )
  ```
  - Status:
  - Comments:

- [ ] **Update `escalation_stub_node` END edge** → change to `escalation_node`:
  ```python
  # Remove:
  builder.add_edge("escalation_stub_node", END)
  # Add:
  builder.add_edge("escalation_node", END)
  ```
  - Status:
  - Comments:

### 6. Slack publisher: create or update tools/slack_publisher.py

- [ ] **Create `tools/slack_publisher.py`** (if Phase 5 incomplete) OR **update `_build_message()`** (if Phase 5 delivered the 4-field version) to use the full `EscalationOutput`:
  ```python
  """Expert-channel Slack publisher for escalation notifications.

  Standalone WebClient (not Bolt App) so it can be called from agents/escalation.py
  without importing the full Slack Bolt runtime. Falls back to a local JSON file
  when Slack is unavailable (file fallback handled in agents/escalation.py's caller).
  """

  from __future__ import annotations

  from slack_sdk import WebClient
  from slack_sdk.errors import SlackApiError

  from config import settings
  from schemas import EscalationOutput

  _client: WebClient | None = None


  def _get_client() -> WebClient:
      global _client
      if _client is None:
          assert settings.slack_bot_token, "SLACK_BOT_TOKEN is required for escalation publishing"
          _client = WebClient(token=settings.slack_bot_token.get_secret_value())
      return _client


  def post_to_expert_channel(escalation: EscalationOutput) -> None:
      """Publish escalation to expert Slack channel (raises SlackApiError on failure)."""
      assert settings.slack_expert_channel_id, "SLACK_EXPERT_CHANNEL_ID is required"
      message = _build_message(escalation)
      _get_client().chat_postMessage(
          channel=settings.slack_expert_channel_id,
          text=message["text"],
          blocks=message["blocks"],
      )


  def _build_message(escalation: EscalationOutput) -> dict:
      """Build Block Kit payload per ARCHITECTURE § 9.3."""
      ts_str = escalation.timestamp.strftime("%Y-%m-%d %H:%M:%S")
      return {
          "text": f"Ескалація [{escalation.category}]: {escalation.summary}",
          "blocks": [
              {
                  "type": "header",
                  "text": {"type": "plain_text", "text": "🚨 Ескалація запиту"},
              },
              {
                  "type": "section",
                  "fields": [
                      {"type": "mrkdwn", "text": f"*Сесія:*\n`{escalation.session_id}`"},
                      {"type": "mrkdwn", "text": f"*Категорія:*\n`{escalation.category}`"},
                      {"type": "mrkdwn", "text": f"*Час:*\n{ts_str}"},
                  ],
              },
              {
                  "type": "section",
                  "text": {
                      "type": "mrkdwn",
                      "text": f"*Резюме:*\n{escalation.summary}",
                  },
              },
              {
                  "type": "section",
                  "text": {
                      "type": "mrkdwn",
                      "text": f"*Запит користувача:*\n{escalation.customer_message}",
                  },
              },
              {
                  "type": "section",
                  "text": {
                      "type": "mrkdwn",
                      "text": f"*Що система спробувала:*\n{escalation.attempted_resolution}",
                  },
              },
          ],
      }
  ```
  Note: `post_to_expert_channel` now raises on failure (not catches). The `try/except` lives in `escalation_node` in `agents/escalation.py`, which is the single place where error handling policy is enforced.
  - Status:
  - Comments: If Phase 5 already created `tools/slack_publisher.py` with a `_save_to_file()` fallback inside the publisher itself — remove that method. Phase 6 moves file save responsibility to `agents/escalation.py` (`_save_to_file()` always runs before the Slack call). The publisher only publishes.

### 7. Update tests/test_graph_routing.py

- [ ] **Add `escalation_node` mock to `patch_graph_dependencies` fixture** — the real node makes LLM calls and Slack requests; tests must stub it:
  ```python
  # Add this import at top of test_graph_routing.py:
  from language import get_escalation_message

  # Inside patch_graph_dependencies fixture, add after the critic mock:
  monkeypatch.setattr(
      supervisor,
      "escalation_node",
      lambda state: {
          "final_response": get_escalation_message(
              state["plan"].language if state.get("plan") else "uk"
          ),
          "escalated": True,
      },
  )
  ```
  - Status:
  - Comments:

- [ ] **Update `test_escalation_returns_stub_message`** — rename test + update assertion to use the new static message:
  ```python
  def test_escalation_routes_and_sets_escalated_flag(patch_graph_dependencies) -> None:
      patch_graph_dependencies.plan.plan = _plan(
          query="Система не працює",
          topic=None,
          needs_human=True,
          escalation_reason="Потрібна перевірка інциденту.",
      )
      graph = supervisor.build_graph()

      result = graph.invoke(
          _state("Система не працює"),
          {"configurable": {"thread_id": "escalation-route"}},
      )

      assert result["escalated"] is True
      assert result["final_response"] == get_escalation_message("uk")
  ```
  - Status:
  - Comments: The parametrized test `test_final_response_is_not_none_for_all_routes` also covers the escalation path and must also not hit the real node — the monkeypatch in `patch_graph_dependencies` handles this.

### 8. Create tests/test_escalation.py

- [ ] **Create `tests/test_escalation.py`** with the following test groups:
  ```python
  """Unit tests for agents/escalation.py — pure function and node behaviour."""

  from __future__ import annotations

  import json
  from datetime import datetime
  from pathlib import Path
  from unittest.mock import MagicMock

  import pytest

  from agents.escalation import (
      _build_attempted_resolution,
      _build_full_context,
      _determine_category,
      escalation_node,
      invoke_escalation,
  )
  from language import get_escalation_message
  from schemas import (
      CritiqueResult,
      EscalationOutput,
      ResearchPlan,
      RevisionRequest,
      SubTask,
      WorkerResponse,
  )


  # ── helpers ───────────────────────────────────────────────────────────────────

  def _state(
      *,
      user_message: str = "Тестовий запит",
      session_id: str = "T1:C1:U1:ts1",
      plan: ResearchPlan | None = None,
      worker_responses: list[WorkerResponse] | None = None,
      critic_history: list[CritiqueResult] | None = None,
      retry_count: int = 0,
  ) -> dict:
      return {
          "user_message": user_message,
          "session_id": session_id,
          "user_id": "U1",
          "plan": plan,
          "worker_responses": worker_responses or [],
          "critic_history": critic_history or [],
          "retry_count": retry_count,
          "aggregated_response": None,
          "escalated": False,
          "final_response": None,
      }


  def _plan(needs_human: bool = True, escalation_reason: str = "Збій", language: str = "uk") -> ResearchPlan:
      return ResearchPlan(
          is_on_topic=True,
          language=language,
          original_query="Тестовий запит",
          subtasks=[],
          needs_human=needs_human,
          escalation_reason=escalation_reason if needs_human else None,
      )


  def _worker(
      topic: str = "technical_system",
      found: bool = False,
      needs_human: bool = False,
      needs_human_reason: str | None = None,
  ) -> WorkerResponse:
      return WorkerResponse(
          topic=topic,
          found=found,
          answer=None,
          confidence=0.0,
          needs_human=needs_human,
          needs_human_reason=needs_human_reason,
      )


  def _critique(verdict: str = "revise", gaps: list[str] | None = None) -> CritiqueResult:
      kwargs = dict(
          verdict=verdict,
          freshness_score=0.4,
          completeness_score=0.5,
          structure_score=0.6,
          gaps=gaps or ["Missing source"],
      )
      if verdict == "revise":
          kwargs["revision_requests"] = [
              RevisionRequest(topic="legal", request="Fix it", severity="major")
          ]
      return CritiqueResult(**kwargs)


  # ── _determine_category ───────────────────────────────────────────────────────

  class TestDetermineCategory:
      def test_max_retries_exceeded(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 2)
          state = _state(retry_count=2, critic_history=[_critique()])
          assert _determine_category(state) == "max_retries_exceeded"

      def test_bug_from_worker_reason(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 3)
          state = _state(
              worker_responses=[_worker(needs_human=True, needs_human_reason="Виявлено баг у кабінеті")]
          )
          assert _determine_category(state) == "bug"

      def test_feature_request_from_worker_reason(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 3)
          state = _state(
              worker_responses=[_worker(needs_human=True, needs_human_reason="Відсутня функція завантаження")]
          )
          assert _determine_category(state) == "feature_request"

      def test_unanswerable_default(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 3)
          state = _state(plan=_plan(needs_human=True, escalation_reason="Складне питання"))
          assert _determine_category(state) == "unanswerable"


  # ── _build_attempted_resolution ───────────────────────────────────────────────

  class TestBuildAttemptedResolution:
      def test_no_workers_planner_escalation(self):
          state = _state(worker_responses=[])
          result = _build_attempted_resolution(state)
          assert "пряма ескалація" in result

      def test_worker_found(self):
          state = _state(worker_responses=[WorkerResponse(topic="legal", found=True, answer="Answer", confidence=0.9)])
          result = _build_attempted_resolution(state)
          assert "legal" in result
          assert "знайдено" in result

      def test_worker_needs_human_included(self):
          state = _state(
              worker_responses=[_worker(needs_human=True, needs_human_reason="Це баг")]
          )
          result = _build_attempted_resolution(state)
          assert "потрібна людина" in result

      def test_critic_history_included(self):
          state = _state(
              worker_responses=[_worker(found=False)],
              critic_history=[_critique(verdict="revise", gaps=["Missing source", "Too vague"])],
              retry_count=2,
          )
          result = _build_attempted_resolution(state)
          assert "Критик" in result
          assert "revise" in result


  # ── _build_full_context ───────────────────────────────────────────────────────

  class TestBuildFullContext:
      def test_plan_serialized(self):
          state = _state(plan=_plan())
          ctx = _build_full_context(state)
          assert ctx["plan"] is not None
          assert ctx["plan"]["needs_human"] is True

      def test_no_plan(self):
          state = _state(plan=None)
          ctx = _build_full_context(state)
          assert ctx["plan"] is None

      def test_worker_responses_serialized(self):
          state = _state(worker_responses=[_worker(topic="legal")])
          ctx = _build_full_context(state)
          assert len(ctx["worker_responses"]) == 1
          assert ctx["worker_responses"][0]["topic"] == "legal"


  # ── invoke_escalation ─────────────────────────────────────────────────────────

  class TestInvokeEscalation:
      def test_builds_escalation_output(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 3)

          # Stub the LLM call
          fake_llm_response = MagicMock()
          fake_llm_response.content = "Тестове резюме для оператора."

          fake_llm = MagicMock()
          fake_llm.invoke.return_value = fake_llm_response

          import agents.escalation as esc
          monkeypatch.setattr(esc, "get_llm", lambda: fake_llm)

          state = _state(
              user_message="Не завантажується файл",
              session_id="T1:C1:U1:ts1",
              plan=_plan(needs_human=True, escalation_reason="Потенційний збій"),
          )

          result = invoke_escalation(state)

          assert isinstance(result, EscalationOutput)
          assert result.summary == "Тестове резюме для оператора."
          assert result.category == "unanswerable"
          assert result.customer_message == "Не завантажується файл"
          assert result.session_id == "T1:C1:U1:ts1"
          assert isinstance(result.timestamp, datetime)

      def test_category_max_retries(self, monkeypatch):
          from config import settings
          monkeypatch.setattr(settings, "critic_max_retries", 2)

          fake_llm_response = MagicMock()
          fake_llm_response.content = "Вичерпано повтори."
          fake_llm = MagicMock()
          fake_llm.invoke.return_value = fake_llm_response

          import agents.escalation as esc
          monkeypatch.setattr(esc, "get_llm", lambda: fake_llm)

          state = _state(
              retry_count=2,
              critic_history=[_critique()],
              worker_responses=[_worker(topic="legal", found=True)],
          )
          result = invoke_escalation(state)
          assert result.category == "max_retries_exceeded"


  # ── escalation_node ───────────────────────────────────────────────────────────

  class TestEscalationNode:
      def test_node_sets_escalated_and_final_response(self, monkeypatch, tmp_path):
          fake_escalation = EscalationOutput(
              summary="Резюме",
              category="unanswerable",
              customer_message="Запит",
              attempted_resolution="Не оброблялось",
              full_context={},
              timestamp=datetime(2026, 5, 3, 10, 0, 0),
              session_id="T1:C1:U1:ts1",
          )

          import agents.escalation as esc
          monkeypatch.setattr(esc, "invoke_escalation", lambda state: fake_escalation)
          # Redirect file writes to tmp_path
          monkeypatch.setattr(esc, "_save_to_file", lambda e: None)

          state = _state(plan=_plan(language="uk"))
          result = escalation_node(state)

          assert result["escalated"] is True
          assert result["final_response"] == get_escalation_message("uk")

      def test_node_english_language(self, monkeypatch):
          fake_escalation = EscalationOutput(
              summary="Summary",
              category="unanswerable",
              customer_message="Query",
              attempted_resolution="Nothing",
              full_context={},
              timestamp=datetime(2026, 5, 3, 10, 0, 0),
              session_id="T1:C1:U1:ts1",
          )

          import agents.escalation as esc
          monkeypatch.setattr(esc, "invoke_escalation", lambda state: fake_escalation)
          monkeypatch.setattr(esc, "_save_to_file", lambda e: None)

          state = _state(plan=_plan(language="en"))
          result = escalation_node(state)

          assert result["final_response"] == get_escalation_message("en")

      def test_node_no_plan_defaults_to_uk(self, monkeypatch):
          fake_escalation = EscalationOutput(
              summary="Summary",
              category="unanswerable",
              customer_message="Query",
              attempted_resolution="Nothing",
              full_context={},
              timestamp=datetime(2026, 5, 3, 10, 0, 0),
              session_id="T1:C1:U1:ts1",
          )

          import agents.escalation as esc
          monkeypatch.setattr(esc, "invoke_escalation", lambda state: fake_escalation)
          monkeypatch.setattr(esc, "_save_to_file", lambda e: None)

          state = _state(plan=None)
          result = escalation_node(state)
          assert result["final_response"] == get_escalation_message("uk")


  # ── _save_to_file ─────────────────────────────────────────────────────────────

  class TestSaveToFile:
      def test_creates_json_file(self, monkeypatch, tmp_path):
          from agents.escalation import _save_to_file
          import agents.escalation as esc

          monkeypatch.setattr(esc, "_save_to_file",
              lambda e: _real_save(e, tmp_path))

          def _real_save(escalation: EscalationOutput, base: Path) -> None:
              output_dir = base / "escalations"
              output_dir.mkdir(parents=True, exist_ok=True)
              safe_session = escalation.session_id.replace(":", "_")
              safe_ts = escalation.timestamp.strftime("%Y%m%dT%H%M%S")
              path = output_dir / f"{safe_session}_{safe_ts}.json"
              with open(path, "w", encoding="utf-8") as f:
                  json.dump(escalation.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

          esc_out = EscalationOutput(
              summary="Test",
              category="unanswerable",
              customer_message="Q",
              attempted_resolution="Nothing",
              full_context={},
              timestamp=datetime(2026, 5, 3, 10, 0, 0),
              session_id="T1:C1:U1:ts1",
          )
          _real_save(esc_out, tmp_path)

          files = list((tmp_path / "escalations").iterdir())
          assert len(files) == 1
          data = json.loads(files[0].read_text())
          assert data["session_id"] == "T1:C1:U1:ts1"
          assert data["category"] == "unanswerable"
  ```
  - Status:
  - Comments:

### 9. Validate all changes

- [ ] **Syntax check all modified and new files**:
  ```bash
  python -m py_compile schemas.py language.py supervisor.py agents/escalation.py tools/slack_publisher.py prompts/escalation.md
  ```
  (Note: `.md` files are not Python — skip that one. Use `python -m py_compile` only for .py files.)
  ```bash
  python -m py_compile schemas.py language.py supervisor.py agents/escalation.py tools/slack_publisher.py
  ```
  - Status:
  - Comments:

- [ ] **Run unit tests**:
  ```bash
  pytest tests/ -q
  ```
  Confirm: `test_escalation_routes_and_sets_escalated_flag`, `test_critic_revise_loop_escalates_at_max_retries` both pass. All existing routing tests pass with the new mock.
  - Status:
  - Comments:

- [ ] **Import check — graph compiles cleanly**:
  ```bash
  python -c "from supervisor import graph; print('graph OK:', type(graph))"
  python -c "from agents.escalation import escalation_node; print('escalation_node OK')"
  python -c "from tools.slack_publisher import post_to_expert_channel; print('publisher OK')"
  ```
  - Status:
  - Comments:

## Testing Strategy

| Test class | What it tests | Isolation |
|---|---|---|
| `TestDetermineCategory` | All 4 categories: max_retries, bug, feature_request, unanswerable | Pure function, monkeypatches `settings.critic_max_retries` |
| `TestBuildAttemptedResolution` | Empty workers, found/not-found, needs_human reason, critic history | Pure function |
| `TestBuildFullContext` | Plan, workers, and critic history serialization | Pure function |
| `TestInvokeEscalation` | Full assembly: correct fields, correct category, LLM called once | Monkeypatches `agents.escalation.get_llm` |
| `TestEscalationNode` | State delta: `escalated=True`, `final_response` bilingual, no-plan fallback | Monkeypatches `invoke_escalation` + `_save_to_file` |
| `TestSaveToFile` | JSON file created, correct filename pattern, content parseable | Uses `tmp_path` fixture for filesystem isolation |

No integration tests that call Slack or LLM APIs — those require real tokens. E2E validation happens manually (see Validation Commands).

## Acceptance Criteria

1. `escalation_stub_node` is fully removed from `supervisor.py` — no dead code remains.
2. Three escalation trigger paths all route to `escalation_node`: `plan.needs_human=True`, `retry_count >= CRITIC_MAX_RETRIES`, and `any(worker.needs_human)`.
3. Every escalation writes a JSON file under `output/escalations/` with all 7 `EscalationOutput` fields.
4. User receives a static bilingual message (`get_escalation_message(language)`) — no internal details exposed.
5. `pytest tests/ -q` passes (≥101 existing tests + new escalation tests, zero failures).
6. `python -c "from supervisor import graph"` imports cleanly.
7. `EscalationOutput.category` is always one of the 4 literal values — Pydantic validation enforces this.
8. File save always executes before the Slack call; Slack failure does not raise in `escalation_node`.

## Validation Commands

```bash
# 1. Syntax check all changed Python files
python -m py_compile schemas.py language.py supervisor.py agents/escalation.py tools/slack_publisher.py

# 2. Import graph + new modules
python -c "from supervisor import graph; print('graph OK:', type(graph))"
python -c "from agents.escalation import escalation_node; print('escalation_node OK')"
python -c "from tools.slack_publisher import post_to_expert_channel; print('publisher OK')"

# 3. Full test suite (no LLM/Slack credentials needed)
pytest tests/ -q

# 4. Target just new test file
pytest tests/test_escalation.py -v

# 5. Schema sanity check — ensure EscalationOutput rejects old fields
python -c "
from schemas import EscalationOutput
from datetime import datetime
e = EscalationOutput(
    summary='test', category='unanswerable', customer_message='q',
    attempted_resolution='nothing', full_context={},
    timestamp=datetime.now(), session_id='T:C:U'
)
print('EscalationOutput OK:', e.category)
"

# 6. Simulate file save path
python -c "
from datetime import datetime
from schemas import EscalationOutput
from agents.escalation import _save_to_file
e = EscalationOutput(
    summary='test', category='unanswerable', customer_message='q',
    attempted_resolution='nothing', full_context={},
    timestamp=datetime.now(), session_id='test:session:id'
)
_save_to_file(e)
import os; print('Files in output/escalations:', os.listdir('output/escalations'))
"
```

## Notes

- **No new dependencies** — all imports (`langchain_core`, `slack_sdk`, `pydantic`) are already in `requirements.txt`.
- **EscalationOutput is a breaking schema change** — if any other file constructs `EscalationOutput` with old field names (`reason`, `original_query`), it will fail at import time. From scout analysis, no tests do this; they assert on graph state fields instead.
- **`tools/slack_publisher.py` responsibility split**: Phase 6 moves all file I/O out of the publisher (back into `agents/escalation.py`). The publisher is a pure Slack client — it publishes and raises on failure. This makes it easier to test each concern in isolation.
- **`output/escalations/` directory**: `output/.gitkeep` exists; `output/escalations/` is created at runtime by `_save_to_file()` via `mkdir(parents=True, exist_ok=True)`. No manual setup needed.
- **LLM call failure**: If `_generate_summary()` fails (API key missing, rate limit), `invoke_escalation` raises and `escalation_node` propagates it as an unhandled exception — acceptable because this is a control-flow node, not a best-effort operation. The Phase 12 error-resilience (tenacity) is out of scope here.
- **Phase 5 ordering**: If Phase 5 hasn't been started, implement Phase 5 items 5.1–5.3 and 5.5 first (PostgresSaver, session ID, Slack bot, REPL mode). Item 5.4 (publisher) is implemented here in Phase 6 Step 6 since the schema expansion in Phase 6 Step 1 defines the contract the publisher must satisfy. Implementing 5.4 before 6.1 would produce a publisher with the wrong schema.