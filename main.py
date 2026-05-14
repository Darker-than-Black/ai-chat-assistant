"""Entry point: Slack Bolt app backed by the supervisor graph."""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

from psycopg import Connection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import settings
from observability.callbacks import get_langfuse_handler
from schemas import GraphState
from supervisor import build_graph

# Register all Pydantic models that appear in GraphState so LangGraph's
# msgpack deserializer can restore them without warnings (or errors in strict mode).
_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("schemas", "ResearchPlan"),
        ("schemas", "SubTask"),
        ("schemas", "WorkerResponse"),
        ("schemas", "Source"),
        ("schemas", "CritiqueResult"),
        ("schemas", "RevisionRequest"),
    ]
)


@contextmanager
def make_checkpointer() -> Iterator[PostgresSaver]:
    with Connection.connect(
        settings.postgres_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    ) as conn:
        yield PostgresSaver(conn, serde=_SERDE)


def sanitize_terminal_text(text: str) -> str:
    return text.encode("utf-8", errors="surrogateescape").decode(
        "utf-8",
        errors="replace",
    )


def make_session_id(team_id: str, channel_id: str, user_id: str, thread_ts: str | None = None) -> str:
    base = f"{team_id}:{channel_id}:{user_id}"
    if thread_ts:
        return f"{base}:{thread_ts}"
    return base


def build_initial_state(user_message: str, session_id: str, user_id: str = "slack-user") -> GraphState:
    return {
        "user_message": sanitize_terminal_text(user_message),
        "session_id": session_id,
        "user_id": user_id,
        "plan": None,
        "worker_responses": [],
        "critic_history": [],
        "retry_count": 0,
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


def run_slack_app(graph: Any) -> None:
    if not settings.slack_bot_token:
        print("Error: SLACK_BOT_TOKEN is missing from .env")
        sys.exit(1)

    socket_mode = bool(settings.slack_app_token)
    if not socket_mode and not settings.slack_signing_secret:
        print("Error: either SLACK_APP_TOKEN (Socket Mode) or SLACK_SIGNING_SECRET (HTTP mode) must be set")
        sys.exit(1)

    app = App(
        token=settings.slack_bot_token.get_secret_value(),
        signing_secret=settings.slack_signing_secret.get_secret_value() if settings.slack_signing_secret else "",
    )

    @app.event("message")
    def handle_message_events() -> None:
        pass  # bot responds only to app_mention; silence Bolt's unhandled-event warning

    @app.event("app_mention")
    def handle_app_mention_events(body: dict, say: Any) -> None:
        event = body.get("event", {})
        team_id = body.get("team_id", "unknown_team")
        channel_id = event.get("channel", "")
        user_id = event.get("user", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        text = event.get("text", "")

        if settings.slack_user_channel_id and channel_id != settings.slack_user_channel_id:
            return

        session_id = make_session_id(team_id, channel_id, user_id, thread_ts)
        clean_text = text.split(">", 1)[-1].strip() if ">" in text else text

        initial_state = build_initial_state(clean_text, session_id, user_id)
        config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
            config["metadata"] = {
                "langfuse_user_id": user_id,
                "langfuse_session_id": session_id,
                "langfuse_tags": ["procurement-support", "slack"],
            }

        try:
            result = graph.invoke(initial_state, config)
            say(text=result["final_response"], thread_ts=thread_ts)
        except Exception:
            logger.exception("Graph invocation failed for session %s", session_id)
            say(
                text="Вибачте, під час обробки вашого запиту сталася технічна помилка. Спробуйте, будь ласка, ще раз.",
                thread_ts=thread_ts,
            )

    if socket_mode:
        print("Starting Slack Bolt App in Socket Mode...")
        SocketModeHandler(app, settings.slack_app_token.get_secret_value()).start()
    else:
        print("Starting Slack Bolt App on port 3000 (HTTP mode — needs public URL)...")
        app.start(port=3000)


def main() -> None:
    with make_checkpointer() as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        run_slack_app(graph)


if __name__ == "__main__":
    main()
