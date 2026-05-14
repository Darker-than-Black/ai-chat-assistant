from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

import supervisor
from language import get_escalation_message
from schemas import CritiqueResult, ResearchPlan, RevisionRequest, SubTask, WorkerResponse


def _state(user_message: str = "test query") -> dict:
    return {
        "user_message": user_message,
        "session_id": "session-1",
        "user_id": "user-1",
        "plan": None,
        "worker_responses": [],
        "critic_history": [],
        "retry_count": 0,
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


def _plan(
    *,
    query: str,
    topic: str | None = None,
    topics: list[str] | None = None,
    is_on_topic: bool = True,
    needs_human: bool = False,
    off_topic_reason: str | None = None,
    escalation_reason: str | None = None,
    language: str = "uk",
) -> ResearchPlan:
    subtasks: list[SubTask] = []
    if topic is not None:
        subtasks.append(SubTask(topic=topic, query=query, rationale=f"Route to {topic}"))
    if topics is not None:
        for t in topics:
            subtasks.append(SubTask(topic=t, query=f"Q for {t}", rationale=f"Route to {t}"))

    return ResearchPlan(
        is_on_topic=is_on_topic,
        off_topic_reason=off_topic_reason,
        language=language,
        original_query=query,
        subtasks=subtasks,
        needs_human=needs_human,
        escalation_reason=escalation_reason,
    )


def _response(topic: str, answer: str) -> WorkerResponse:
    return WorkerResponse(
        topic=topic,
        found=True,
        answer=answer,
        confidence=0.9,
    )


def _critique_approve() -> CritiqueResult:
    return CritiqueResult(
        verdict="approve",
        freshness_score=0.9,
        completeness_score=0.9,
        structure_score=0.9,
        summary="OK",
    )


def _critique_revise(topic: str = "legal") -> CritiqueResult:
    # Scores intentionally low (avg=0.2) so they stay below critic_min_approve_score
    # and the revise loop correctly escalates after max retries.
    return CritiqueResult(
        verdict="revise",
        freshness_score=0.2,
        completeness_score=0.2,
        structure_score=0.2,
        revision_requests=[
            RevisionRequest(topic=topic, request="Уточни джерело.", severity="major")  # type: ignore[arg-type]
        ],
    )


@pytest.fixture
def patch_graph_dependencies(monkeypatch: pytest.MonkeyPatch):
    plan_holder = SimpleNamespace(plan=None)
    critique_holder = SimpleNamespace(critique=_critique_approve())

    lawyer_response = _response("legal", "Legal answer")
    common_response = _response("procurement_general", "General answer")
    technical_response = _response("technical_system", "Technical answer")

    monkeypatch.setattr(
        supervisor,
        "invoke_planner",
        lambda query: plan_holder.plan,
    )
    monkeypatch.setattr(
        supervisor,
        "lawyer_node",
        lambda state: {"worker_responses": [lawyer_response]},
    )
    monkeypatch.setattr(
        supervisor,
        "common_support_node",
        lambda state: {"worker_responses": [common_response]},
    )
    monkeypatch.setattr(
        supervisor,
        "technical_support_node",
        lambda state: {"worker_responses": [technical_response]},
    )

    def fake_critic_node(state):
        prior = state.get("critic_history", [])
        return {
            "critic_history": prior + [critique_holder.critique],
            "retry_count": state.get("retry_count", 0) + 1,
        }

    monkeypatch.setattr(supervisor, "critic_node", fake_critic_node)

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

    return SimpleNamespace(plan=plan_holder, critique=critique_holder)


def test_legal_query_routes_to_lawyer(patch_graph_dependencies) -> None:
    patch_graph_dependencies.plan.plan = _plan(query="Стаття 17", topic="legal")
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Стаття 17"),
        {"configurable": {"thread_id": "legal-route"}},
    )

    topics = {r.topic for r in result["worker_responses"]}
    assert "legal" in topics


def test_general_query_routes_to_common_support(patch_graph_dependencies) -> None:
    patch_graph_dependencies.plan.plan = _plan(
        query="Етапи відкритих торгів",
        topic="procurement_general",
    )
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Етапи відкритих торгів"),
        {"configurable": {"thread_id": "general-route"}},
    )

    topics = {r.topic for r in result["worker_responses"]}
    assert "procurement_general" in topics


def test_technical_query_routes_to_technical_support(patch_graph_dependencies) -> None:
    patch_graph_dependencies.plan.plan = _plan(
        query="Не завантажується файл",
        topic="technical_system",
    )
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Не завантажується файл"),
        {"configurable": {"thread_id": "technical-route"}},
    )

    topics = {r.topic for r in result["worker_responses"]}
    assert "technical_system" in topics


def test_off_topic_query_returns_refusal(patch_graph_dependencies) -> None:
    patch_graph_dependencies.plan.plan = _plan(
        query="Яка погода завтра?",
        is_on_topic=False,
        topic=None,
        off_topic_reason="Запит не стосується публічних закупівель.",
    )
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Яка погода завтра?"),
        {"configurable": {"thread_id": "off-topic-route"}},
    )

    assert result["worker_responses"] == []
    assert "поза межами системи ProZorro" in result["final_response"]


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


def test_multi_topic_fan_out_collects_all_responses(patch_graph_dependencies) -> None:
    patch_graph_dependencies.plan.plan = _plan(
        query="Стаття 17 і де подати пропозицію в кабінеті?",
        topics=["legal", "technical_system"],
    )
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Стаття 17 і де подати пропозицію в кабінеті?"),
        {"configurable": {"thread_id": "multi-topic-route"}},
    )

    topics = {r.topic for r in result["worker_responses"]}
    assert topics == {"legal", "technical_system"}


def test_multi_topic_fan_out_runs_workers_in_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delay_seconds = 0.35
    plan = _plan(
        query="Стаття 17, етапи торгів і подання пропозиції в кабінеті",
        topics=["legal", "procurement_general", "technical_system"],
    )

    monkeypatch.setattr(supervisor, "invoke_planner", lambda query: plan)

    def delayed_node(topic: str, answer: str):
        def _node(state: dict) -> dict:
            time.sleep(delay_seconds)
            return {"worker_responses": [_response(topic, answer)]}

        return _node

    monkeypatch.setattr(
        supervisor,
        "lawyer_node",
        delayed_node("legal", "Legal answer"),
    )
    monkeypatch.setattr(
        supervisor,
        "common_support_node",
        delayed_node("procurement_general", "General answer"),
    )
    monkeypatch.setattr(
        supervisor,
        "technical_support_node",
        delayed_node("technical_system", "Technical answer"),
    )

    monkeypatch.setattr(
        supervisor,
        "critic_node",
        lambda state: {
            "critic_history": state.get("critic_history", []) + [_critique_approve()],
            "retry_count": state.get("retry_count", 0) + 1,
        },
    )

    graph = supervisor.build_graph()

    started_at = time.perf_counter()
    result = graph.invoke(
        _state(plan.original_query),
        {"configurable": {"thread_id": "parallel-fanout-route"}},
    )
    elapsed = time.perf_counter() - started_at

    topics = {response.topic for response in result["worker_responses"]}
    assert topics == {"legal", "procurement_general", "technical_system"}
    assert elapsed < (delay_seconds * 2)


def test_critic_revise_loop_escalates_at_max_retries(
    monkeypatch: pytest.MonkeyPatch, patch_graph_dependencies
) -> None:
    from config import settings

    monkeypatch.setattr(settings, "critic_max_retries", 2)
    patch_graph_dependencies.critique.critique = _critique_revise(topic="legal")
    patch_graph_dependencies.plan.plan = _plan(query="Стаття 17", topic="legal")

    graph = supervisor.build_graph()

    result = graph.invoke(
        _state("Стаття 17"),
        {"configurable": {"thread_id": "revise-loop"}},
    )

    assert result["escalated"] is True
    assert result["retry_count"] >= 2


@pytest.mark.parametrize(
    ("plan_factory", "thread_id"),
    [
        (lambda: _plan(query="Стаття 17", topic="legal"), "final-legal"),
        (
            lambda: _plan(query="Етапи відкритих торгів", topic="procurement_general"),
            "final-general",
        ),
        (
            lambda: _plan(query="Не завантажується файл", topic="technical_system"),
            "final-technical",
        ),
        (
            lambda: _plan(
                query="Яка погода завтра?",
                is_on_topic=False,
                topic=None,
                off_topic_reason="Запит не стосується публічних закупівель.",
            ),
            "final-off-topic",
        ),
        (
            lambda: _plan(
                query="Система не працює",
                topic=None,
                needs_human=True,
                escalation_reason="Потрібна перевірка інциденту.",
            ),
            "final-escalation",
        ),
    ],
)
def test_final_response_is_not_none_for_all_routes(
    patch_graph_dependencies,
    plan_factory,
    thread_id: str,
) -> None:
    plan = plan_factory()
    patch_graph_dependencies.plan.plan = plan
    graph = supervisor.build_graph()

    result = graph.invoke(
        _state(plan.original_query),
        {"configurable": {"thread_id": thread_id}},
    )

    assert result["final_response"] is not None
