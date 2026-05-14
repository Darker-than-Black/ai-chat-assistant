"""Tests for the Slack publisher tool."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from slack_sdk.errors import SlackApiError

from schemas import EscalationOutput
from tools.slack_publisher import _build_message, post_to_expert_channel


def build_mock_escalation() -> EscalationOutput:
    return EscalationOutput(
        summary="User is confused about everything.",
        category="feature_request",
        customer_message="Please build me a new feature.",
        attempted_resolution="We searched the db, found nothing.",
        full_context={
            "plan": {"subtasks": [{"topic": "legal", "query": "find feature"}]},
            "critic_history": [{"gaps": ["No relevant sources found."]}],
        },
        timestamp=datetime(2023, 10, 1, 12, 0, 0),
        session_id="session-123",
    )


def test_build_message() -> None:
    esc = build_mock_escalation()
    msg = _build_message(esc)

    assert "Ескалація [feature_request]: User is confused about everything." in msg["text"]
    
    # Check that we have the right number of blocks
    blocks = msg["blocks"]
    assert len(blocks) == 5
    
    # Check header
    assert blocks[0]["type"] == "header"
    
    # Check fields (session, category, timestamp)
    fields = blocks[1]["fields"]
    assert any("session-123" in f["text"] for f in fields)
    assert any("feature_request" in f["text"] for f in fields)
    assert any("2023-10-01 12:00:00" in f["text"] for f in fields)
    
    # Check summary
    assert "User is confused about everything." in blocks[2]["text"]["text"]
    
    # Check customer message
    assert "Please build me a new feature." in blocks[3]["text"]["text"]
    
    # Check attempted resolution
    assert "We searched the db, found nothing." in blocks[4]["text"]["text"]


def test_post_to_expert_channel_success(monkeypatch) -> None:
    esc = build_mock_escalation()

    mock_settings = MagicMock()
    mock_settings.slack_bot_token = SecretStr("xoxb-test")
    mock_settings.slack_expert_channel_id = "C12345"
    monkeypatch.setattr("tools.slack_publisher.settings", mock_settings)

    mock_client = MagicMock()
    monkeypatch.setattr("tools.slack_publisher._get_client", lambda: mock_client)

    post_to_expert_channel(esc)

    mock_client.chat_postMessage.assert_called_once()
    kwargs = mock_client.chat_postMessage.call_args[1]
    assert kwargs["channel"] == "C12345"
    assert "Ескалація [feature_request]" in kwargs["text"]
    assert isinstance(kwargs["blocks"], list)


def test_post_to_expert_channel_raises_on_error(monkeypatch) -> None:
    esc = build_mock_escalation()

    mock_settings = MagicMock()
    mock_settings.slack_bot_token = SecretStr("xoxb-test")
    mock_settings.slack_expert_channel_id = "C12345"
    monkeypatch.setattr("tools.slack_publisher.settings", mock_settings)

    mock_client = MagicMock()
    mock_client.chat_postMessage.side_effect = SlackApiError("Error", {"error": "channel_not_found"})
    monkeypatch.setattr("tools.slack_publisher._get_client", lambda: mock_client)

    with pytest.raises(SlackApiError):
        post_to_expert_channel(esc)


def test_post_to_expert_channel_raises_assertion_on_missing_credentials(monkeypatch) -> None:
    esc = build_mock_escalation()

    # Missing expert channel id
    mock_settings = MagicMock()
    mock_settings.slack_bot_token = SecretStr("xoxb-test")
    mock_settings.slack_expert_channel_id = None
    monkeypatch.setattr("tools.slack_publisher.settings", mock_settings)

    with pytest.raises(AssertionError, match="SLACK_EXPERT_CHANNEL_ID is required"):
        post_to_expert_channel(esc)
