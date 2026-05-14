from __future__ import annotations

import main


def test_sanitize_terminal_text_replaces_invalid_surrogates() -> None:
    raw = "запит \udcd0 test"

    assert main.sanitize_terminal_text(raw) == "запит � test"


def test_make_session_id() -> None:
    assert main.make_session_id("T1", "C1", "U1") == "T1:C1:U1"
    assert main.make_session_id("T1", "C1", "U1", "123.456") == "T1:C1:U1:123.456"


def test_build_initial_state_sets_all_graph_fields() -> None:
    state = main.build_initial_state("Тестовий запит", "session-123")

    assert state == {
        "user_message": "Тестовий запит",
        "session_id": "session-123",
        "user_id": "slack-user",
        "plan": None,
        "worker_responses": [],
        "critic_history": [],
        "retry_count": 0,
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


def test_build_initial_state_sanitizes_user_message() -> None:
    state = main.build_initial_state("Тест \udcd0 запит", "session-123")

    assert state["user_message"] == "Тест � запит"
