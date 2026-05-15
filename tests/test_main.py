from __future__ import annotations

from pydantic import SecretStr
import pytest

import main
from config import settings


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


def test_build_bolt_app_requires_signing_secret_for_http(monkeypatch) -> None:
    monkeypatch.setattr(settings, "slack_bot_token", SecretStr("xoxb-test"))
    monkeypatch.setattr(settings, "slack_signing_secret", None)

    with pytest.raises(RuntimeError, match="SLACK_SIGNING_SECRET"):
        main.build_bolt_app(require_signing_secret=True)


def test_create_web_app_exposes_healthcheck(monkeypatch) -> None:
    monkeypatch.setattr(settings, "slack_bot_token", SecretStr("xoxb-test"))
    monkeypatch.setattr(settings, "slack_signing_secret", SecretStr("signing-secret"))
    monkeypatch.setattr(main, "register_slack_handlers", lambda app: None)

    app = main.create_web_app()
    response = app.test_client().get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
