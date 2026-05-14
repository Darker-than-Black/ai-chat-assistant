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
            RevisionRequest(topic="legal", request="Fix it", severity="major") # type: ignore[arg-type]
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

        assert result["escalated"] is True
        assert result["final_response"] == get_escalation_message("en")
