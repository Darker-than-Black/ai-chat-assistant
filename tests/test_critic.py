from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from schemas import (
    CritiqueResult,
    GraphState,
    ResearchPlan,
    RevisionRequest,
    SubTask,
)


class StaticCritiqueRunnable(Runnable[Any, CritiqueResult]):
    def __init__(self, result: CritiqueResult) -> None:
        self.result = result

    def invoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> CritiqueResult:
        return self.result


class FakeStructuredLLM:
    def __init__(self, result: CritiqueResult) -> None:
        self.result = result
        self.schema: type | None = None

    def with_structured_output(
        self, schema: type[CritiqueResult]
    ) -> StaticCritiqueRunnable:
        self.schema = schema
        return StaticCritiqueRunnable(self.result)


def _plan() -> ResearchPlan:
    return ResearchPlan(
        is_on_topic=True,
        original_query="тест",
        subtasks=[SubTask(topic="legal", query="q", rationale="r")],
    )


def _state(retry_count: int = 0, critic_history: list[CritiqueResult] | None = None) -> GraphState:
    return {
        "user_message": "тест",
        "session_id": "s",
        "user_id": "u",
        "plan": _plan(),
        "worker_responses": [],
        "critic_history": critic_history or [],
        "retry_count": retry_count,
        "aggregated_response": "Юридична відповідь",
        "escalated": False,
        "final_response": None,
    }


def test_invoke_critic_returns_critique_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = CritiqueResult(
        verdict="approve",
        freshness_score=0.9,
        completeness_score=0.9,
        structure_score=0.9,
        summary="OK",
    )
    fake_llm = FakeStructuredLLM(expected)
    monkeypatch.setattr("agents.critic.get_llm", lambda: fake_llm)

    from agents.critic import invoke_critic

    plan = _plan()
    result = invoke_critic("Юридична відповідь", plan, [])

    assert result == expected
    assert fake_llm.schema is CritiqueResult


def test_critic_node_appends_history_and_increments_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    critique = CritiqueResult(
        verdict="approve",
        freshness_score=0.9,
        completeness_score=0.9,
        structure_score=0.9,
    )
    monkeypatch.setattr("agents.critic.get_llm", lambda: FakeStructuredLLM(critique))

    from agents.critic import critic_node

    state = _state(retry_count=0, critic_history=[])
    delta = critic_node(state)

    assert delta["retry_count"] == 1
    assert len(delta["critic_history"]) == 1
    assert delta["critic_history"][0] == critique


def test_critic_node_preserves_prior_history(monkeypatch: pytest.MonkeyPatch) -> None:
    prior = CritiqueResult(
        verdict="revise",
        freshness_score=0.4,
        completeness_score=0.5,
        structure_score=0.6,
        revision_requests=[
            RevisionRequest(topic="legal", request="x", severity="major")
        ],
    )
    new = CritiqueResult(
        verdict="approve",
        freshness_score=0.9,
        completeness_score=0.9,
        structure_score=0.9,
    )
    monkeypatch.setattr("agents.critic.get_llm", lambda: FakeStructuredLLM(new))

    from agents.critic import critic_node

    state = _state(retry_count=1, critic_history=[prior])
    delta = critic_node(state)

    assert delta["retry_count"] == 2
    assert delta["critic_history"] == [prior, new]


def test_critique_revise_without_requests_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        CritiqueResult(
            verdict="revise",
            freshness_score=0.4,
            completeness_score=0.5,
            structure_score=0.6,
        )


class TestRouteAfterCritic:
    def _revise(
        self,
        freshness: float = 0.2,
        completeness: float = 0.2,
        structure: float = 0.2,
    ) -> CritiqueResult:
        return CritiqueResult(
            verdict="revise",
            freshness_score=freshness,
            completeness_score=completeness,
            structure_score=structure,
            revision_requests=[
                RevisionRequest(topic="legal", request="x", severity="major")
            ],
        )

    def test_approve_routes_to_final_response(self) -> None:
        from supervisor import route_after_critic

        critique = CritiqueResult(
            verdict="approve",
            freshness_score=0.9,
            completeness_score=0.9,
            structure_score=0.9,
        )
        state = _state(retry_count=1, critic_history=[critique])

        assert route_after_critic(state) == "final_response_node"

    def test_first_revise_with_low_scores_routes_to_redispatch(self) -> None:
        from config import settings
        from supervisor import route_after_critic

        # avg = (0.2+0.2+0.2)/3 = 0.2 < 0.5 — no bypass, even after first retry
        state = _state(retry_count=1, critic_history=[self._revise(0.2, 0.2, 0.2)])

        with patch.object(settings, "critic_max_retries", 3):
            with patch.object(settings, "critic_min_approve_score", 0.5):
                assert route_after_critic(state) == "targeted_redispatcher"

    def test_first_revise_at_retry_zero_always_redispatches(self) -> None:
        from config import settings
        from supervisor import route_after_critic

        # retry_count=0 means we haven't done a revision yet — always redispatch
        state = _state(retry_count=0, critic_history=[self._revise(0.8, 0.8, 0.8)])

        with patch.object(settings, "critic_max_retries", 3):
            with patch.object(settings, "critic_min_approve_score", 0.5):
                assert route_after_critic(state) == "targeted_redispatcher"

    def test_revise_with_adequate_scores_after_retry_approves(self) -> None:
        from config import settings
        from supervisor import route_after_critic

        # avg = (0.6+0.6+0.6)/3 = 0.6 >= 0.5 and retry_count >= 1 → bypass to final
        state = _state(retry_count=1, critic_history=[self._revise(0.6, 0.6, 0.6)])

        with patch.object(settings, "critic_max_retries", 3):
            with patch.object(settings, "critic_min_approve_score", 0.5):
                assert route_after_critic(state) == "final_response_node"

    def test_revise_at_max_retries_routes_to_escalation(self) -> None:
        from config import settings
        from supervisor import route_after_critic

        state = _state(retry_count=3, critic_history=[self._revise(0.2, 0.2, 0.2)])

        with patch.object(settings, "critic_max_retries", 3):
            assert route_after_critic(state) == "escalation_node"

    def test_revise_above_max_retries_routes_to_escalation(self) -> None:
        from config import settings
        from supervisor import route_after_critic

        state = _state(retry_count=5, critic_history=[self._revise(0.2, 0.2, 0.2)])

        with patch.object(settings, "critic_max_retries", 3):
            assert route_after_critic(state) == "escalation_node"
