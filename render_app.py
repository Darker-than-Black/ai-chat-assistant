"""Minimal Flask app for Render.

The web server must open a port quickly so Render can mark the service healthy.
We therefore avoid importing the full assistant stack at module import time and
lazy-load the Slack Bolt handler only on the `/slack/events` route.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

_slack_handler: Any | None = None


def _get_slack_handler():
    global _slack_handler
    if _slack_handler is None:
        from slack_bolt.adapter.flask import SlackRequestHandler

        from main import build_bolt_app

        bolt_app = build_bolt_app(require_signing_secret=True)
        _slack_handler = SlackRequestHandler(bolt_app)
    return _slack_handler


@app.get("/")
def index():
    return jsonify({"ok": True, "service": "prozorro-support-assistant"})


@app.get("/healthz")
def healthcheck():
    return jsonify({"ok": True})


@app.post("/slack/events")
def slack_events():
    return _get_slack_handler().handle(request)
