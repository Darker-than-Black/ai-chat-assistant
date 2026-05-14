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
