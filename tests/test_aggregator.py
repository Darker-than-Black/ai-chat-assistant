from __future__ import annotations

from schemas import GraphState, WorkerResponse
from supervisor import aggregate_responses_node


def _state(responses: list[WorkerResponse]) -> GraphState:
    return {
        "user_message": "test",
        "session_id": "s",
        "user_id": "u",
        "plan": None,
        "worker_responses": responses,
        "critic_history": [],
        "retry_count": 0,
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


def _resp(topic: str, answer: str | None, found: bool = True, confidence: float = 0.8) -> WorkerResponse:
    return WorkerResponse(
        topic=topic,
        found=found,
        answer=answer,
        confidence=confidence,
    )


def test_single_topic_returns_answer_text() -> None:
    state = _state([_resp("legal", "Юридична відповідь")])

    out = aggregate_responses_node(state)

    assert out["aggregated_response"] == "Юридична відповідь"


def test_multi_topic_joined_in_fixed_order() -> None:
    state = _state(
        [
            _resp("technical_system", "Технічно"),
            _resp("legal", "Юридично"),
            _resp("procurement_general", "Загально"),
        ]
    )

    out = aggregate_responses_node(state)

    assert out["aggregated_response"] == "Юридично\n\n---\n\nЗагально\n\n---\n\nТехнічно"


def test_multi_round_best_response_wins() -> None:
    """Best (found=True, highest confidence) response per topic is kept, not the latest."""
    round1 = [
        _resp("legal", "Round1 legal", confidence=0.8),
        _resp("procurement_general", "Round1 general", confidence=0.8),
        _resp("technical_system", "Round1 technical", confidence=0.8),
    ]
    # Revision round produces lower-confidence responses for legal and technical
    round2 = [
        _resp("legal", "Round2 legal revised", confidence=0.6),
        _resp("technical_system", "Round2 technical revised", confidence=0.6),
    ]
    state = _state(round1 + round2)

    out = aggregate_responses_node(state)

    text = out["aggregated_response"]
    # Round1 had higher confidence — they should win
    assert "Round1 legal" in text
    assert "Round1 technical" in text
    assert "Round1 general" in text
    assert "Round2 legal revised" not in text
    assert "Round2 technical revised" not in text


def test_multi_round_higher_confidence_revision_wins() -> None:
    """If revision produces a higher-confidence found=True response, it replaces the initial."""
    round1 = [_resp("legal", "Initial legal", confidence=0.5)]
    round2 = [_resp("legal", "Better legal revised", confidence=0.9)]
    state = _state(round1 + round2)

    out = aggregate_responses_node(state)

    assert "Better legal revised" in out["aggregated_response"]
    assert "Initial legal" not in out["aggregated_response"]


def test_multi_round_found_true_beats_found_false() -> None:
    """A found=True response always wins over found=False regardless of order."""
    round1 = [_resp("legal", "Good answer", found=True, confidence=0.7)]
    round2 = [_resp("legal", None, found=False, confidence=0.3)]
    state = _state(round1 + round2)

    out = aggregate_responses_node(state)

    assert "Good answer" in out["aggregated_response"]


def test_all_not_found_returns_empty_string() -> None:
    state = _state(
        [
            _resp("legal", None, found=False),
            _resp("technical_system", "should be ignored", found=False),
        ]
    )

    out = aggregate_responses_node(state)

    assert out["aggregated_response"] == ""


def test_skips_responses_with_empty_answer() -> None:
    state = _state(
        [
            _resp("legal", None, found=True),
            _resp("procurement_general", "Має текст", found=True),
        ]
    )

    out = aggregate_responses_node(state)

    assert out["aggregated_response"] == "Має текст"


def test_no_responses_returns_empty_string() -> None:
    state = _state([])

    out = aggregate_responses_node(state)

    assert out["aggregated_response"] == ""
