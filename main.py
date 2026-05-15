"""Entry point and app factory for the Slack-backed assistant."""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Iterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from psycopg import Connection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from slack_bolt import App
from slack_sdk.errors import SlackApiError
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

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="slack-worker")


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


def invoke_graph(user_message: str, session_id: str, user_id: str) -> dict[str, Any]:
    initial_state = build_initial_state(user_message, session_id, user_id)
    config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
        config["metadata"] = {
            "langfuse_user_id": user_id,
            "langfuse_session_id": session_id,
            "langfuse_tags": ["procurement-support", "slack"],
        }

    with make_checkpointer() as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        return graph.invoke(initial_state, config)


def _extract_slack_context(body: dict) -> tuple[str, str, str, str | None, str]:
    event = body.get("event", {})
    team_id = body.get("team_id", "unknown_team")
    channel_id = event.get("channel", "")
    user_id = event.get("user", "")
    thread_ts = event.get("thread_ts")
    text = event.get("text", "")
    clean_text = text.split(">", 1)[-1].strip() if ">" in text else text
    return team_id, channel_id, user_id, thread_ts, clean_text


def _post_message(app: App, channel_id: str, thread_ts: str | None, text: str) -> None:
    logger.info(
        "Posting Slack message to channel=%s thread_ts=%s text_len=%s",
        channel_id,
        thread_ts,
        len(text),
    )
    app.client.chat_postMessage(
        channel=channel_id,
        text=text,
        thread_ts=thread_ts,
    )


def _process_app_mention(app: App, body: dict) -> None:
    team_id, channel_id, user_id, thread_ts, clean_text = _extract_slack_context(body)
    logger.info(
        "Received Slack app_mention team=%s channel=%s user=%s thread_ts=%s text=%r",
        team_id,
        channel_id,
        user_id,
        thread_ts,
        clean_text[:200],
    )

    if settings.slack_user_channel_id and channel_id != settings.slack_user_channel_id:
        logger.info(
            "Skipping Slack event for channel=%s; allowed channel=%s",
            channel_id,
            settings.slack_user_channel_id,
        )
        return

    session_id = make_session_id(team_id, channel_id, user_id, thread_ts)

    try:
        result = invoke_graph(clean_text, session_id, user_id)
        _post_message(app, channel_id, thread_ts, result["final_response"])
    except Exception:
        logger.exception("Graph invocation failed for session %s", session_id)
        try:
            _post_message(
                app,
                channel_id,
                thread_ts,
                "Вибачте, під час обробки вашого запиту сталася технічна помилка. Спробуйте, будь ласка, ще раз.",
            )
        except SlackApiError:
            logger.exception("Failed to post Slack error message for session %s", session_id)


def register_slack_handlers(app: App) -> None:
    @app.event("message")
    def handle_message_events() -> None:
        pass  # bot responds only to app_mention; silence Bolt's unhandled-event warning

    @app.event("app_mention")
    def handle_app_mention_events(body: dict) -> None:
        _EXECUTOR.submit(_process_app_mention, app, body)


def build_bolt_app(require_signing_secret: bool) -> App:
    if not settings.slack_bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN is missing from .env")
    if require_signing_secret and not settings.slack_signing_secret:
        raise RuntimeError("SLACK_SIGNING_SECRET is missing from .env")

    app = App(
        token=settings.slack_bot_token.get_secret_value(),
        signing_secret=settings.slack_signing_secret.get_secret_value() if settings.slack_signing_secret else "",
    )
    register_slack_handlers(app)
    return app


def create_web_app() -> Any:
    from flask import Flask, jsonify, request
    from slack_bolt.adapter.flask import SlackRequestHandler

    bolt_app = build_bolt_app(require_signing_secret=True)
    handler = SlackRequestHandler(bolt_app)
    web_app = Flask(__name__)

    @web_app.get("/")
    def index():
        return jsonify({"ok": True, "service": "prozorro-support-assistant"})

    @web_app.get("/healthz")
    def healthcheck():
        return jsonify({"ok": True})

    @web_app.post("/slack/events")
    def slack_events():
        return handler.handle(request)

    return web_app


def run_slack_app() -> None:
    socket_mode = bool(settings.slack_app_token)
    if socket_mode:
        if not settings.slack_app_token:
            print("Error: SLACK_APP_TOKEN is missing from .env")
            sys.exit(1)
        app = build_bolt_app(require_signing_secret=False)
        print("Starting Slack Bolt App in Socket Mode...")
        SocketModeHandler(app, settings.slack_app_token.get_secret_value()).start()
    else:
        app = build_bolt_app(require_signing_secret=True)
        print(f"Starting Slack Bolt App on port {settings.port} (HTTP mode — needs public URL)...")
        app.start(port=settings.port)


def main() -> None:
    run_slack_app()


if __name__ == "__main__":
    main()
