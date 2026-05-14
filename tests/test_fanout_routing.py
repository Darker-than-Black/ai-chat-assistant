from __future__ import annotations

from langgraph.types import Send

from schemas import CritiqueResult, ResearchPlan, RevisionRequest, SubTask
from supervisor import fan_out_send, targeted_redispatch_send


def _state(plan: ResearchPlan, critic_history: list[CritiqueResult] | None = None) -> dict:
    return {
        "user_message": plan.original_query,
        "session_id": "s",
        "user_id": "u",
        "plan": plan,
        "worker_responses": [],
        "critic_history": critic_history or [],
        "retry_count": len(critic_history or []),
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


def _plan(*topics: str) -> ResearchPlan:
    return ResearchPlan(
        is_on_topic=True,
        original_query=" / ".join(topics) or "test",
        subtasks=[
            SubTask(topic=t, query=f"Q for {t}", rationale=f"R for {t}")
            for t in topics
        ],
    )


def test_fan_out_send_single_subtask_targets_correct_node() -> None:
    state = _state(_plan("legal"))

    sends = fan_out_send(state)

    assert len(sends) == 1
    assert isinstance(sends[0], Send)
    assert sends[0].node == "lawyer_node"
    assert sends[0].arg["subtask"].topic == "legal"
    assert sends[0].arg["revision_feedback"] is None


def test_fan_out_send_three_subtasks_targets_three_nodes() -> None:
    state = _state(_plan("legal", "procurement_general", "technical_system"))

    sends = fan_out_send(state)

    assert len(sends) == 3
    targets = {s.node for s in sends}
    assert targets == {"lawyer_node", "common_support_node", "technical_support_node"}
    assert all(s.arg["revision_feedback"] is None for s in sends)


def test_fan_out_send_topic_to_node_mapping() -> None:
    state = _state(_plan("technical_system"))

    sends = fan_out_send(state)

    assert sends[0].node == "technical_support_node"


def test_targeted_redispatch_single_revision() -> None:
    plan = _plan("legal", "procurement_general")
    critique = CritiqueResult(
        verdict="revise",
        freshness_score=0.5,
        completeness_score=0.5,
        structure_score=0.9,
        revision_requests=[
            RevisionRequest(
                topic="legal",
                request="Уточни джерело статті 17.",
                severity="major",
            )
        ],
    )
    state = _state(plan, critic_history=[critique])

    sends = targeted_redispatch_send(state)

    assert len(sends) == 1
    assert sends[0].node == "lawyer_node"
    assert sends[0].arg["revision_feedback"] == "Уточни джерело статті 17."
    assert sends[0].arg["subtask"].topic == "legal"


def test_targeted_redispatch_multiple_revisions() -> None:
    plan = _plan("legal", "procurement_general", "technical_system")
    critique = CritiqueResult(
        verdict="revise",
        freshness_score=0.5,
        completeness_score=0.5,
        structure_score=0.5,
        revision_requests=[
            RevisionRequest(topic="legal", request="Уточни статтю.", severity="major"),
            RevisionRequest(
                topic="technical_system",
                request="Опиши кроки.",
                severity="minor",
            ),
        ],
    )
    state = _state(plan, critic_history=[critique])

    sends = targeted_redispatch_send(state)

    assert len(sends) == 2
    targets = {s.node for s in sends}
    assert targets == {"lawyer_node", "technical_support_node"}


def test_targeted_redispatch_skips_unknown_topic() -> None:
    plan = _plan("legal")
    critique = CritiqueResult(
        verdict="revise",
        freshness_score=0.5,
        completeness_score=0.5,
        structure_score=0.5,
        revision_requests=[
            RevisionRequest(
                topic="technical_system",
                request="Топіка немає в плані",
                severity="major",
            )
        ],
    )
    state = _state(plan, critic_history=[critique])

    sends = targeted_redispatch_send(state)

    assert sends == []


def test_targeted_redispatch_empty_revision_list_returns_empty() -> None:
    plan = _plan("legal")
    critique = CritiqueResult(
        verdict="approve",
        freshness_score=0.9,
        completeness_score=0.9,
        structure_score=0.9,
    )
    state = _state(plan, critic_history=[critique])

    sends = targeted_redispatch_send(state)

    assert sends == []
