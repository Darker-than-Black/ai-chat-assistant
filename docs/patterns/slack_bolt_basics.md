# Slack Bolt basics

## When to use

Building a Slack bot that listens to events (mentions, messages) and posts back. We use Slack Bolt (the official SDK's higher-level framework) over raw `slack_sdk` because event routing, signature verification, and middleware come built-in.

In this project: `main.py` runs a Bolt app listening to `app_mention` in the user channel; `tools/slack_publisher.py` uses the underlying `WebClient` to post to the expert channel.

## Minimal example

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(
    token=settings.slack_bot_token,           # xoxb-...
    signing_secret=settings.slack_signing_secret,
)

@app.event("app_mention")
def handle_mention(event, say, client):
    user_id = event["user"]
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    user_text = event["text"]

    # Build session_id and invoke the agent graph
    session_id = f"{event['team']}:{channel_id}:{user_id}:{thread_ts}"
    response = run_graph(user_text, session_id=session_id, user_id=user_id)

    say(text=response, thread_ts=thread_ts)

# Posting from non-event code (e.g. escalation):
def post_to_expert_channel(message: str):
    app.client.chat_postMessage(
        channel=settings.slack_expert_channel_id,
        text=message,
        # blocks=[...],   # for Block Kit-formatted messages
    )

if __name__ == "__main__":
    SocketModeHandler(app, settings.slack_app_token).start()
```

`SocketModeHandler` keeps a websocket open to Slack — no public HTTP endpoint required, ideal for development. Production deployments can use HTTP mode (`app.start(port=3000)`) behind a real URL.

## Pitfalls

- **Two different tokens.** `xoxb-...` (`SLACK_BOT_TOKEN`) is the bot user token used by `App`. `xapp-...` (`SLACK_APP_TOKEN`) is the app-level token required *only* for Socket Mode. Don't confuse them.
- **`signing_secret`** is for HTTP-mode signature verification. Required even in Socket Mode (some libs check it; it's free to set).
- **Always reply in thread.** Use `thread_ts=event.get("thread_ts") or event["ts"]`. If you reply to the channel root instead of the thread, conversations fragment and `session_id` continuity breaks.
- **Bot must be invited to the channel.** No "auto-join" — humans add the bot. Failing silently because of "not in channel" is a common first-day bug.
- **`event["text"]` includes the mention prefix** (`<@U123>`). Strip it before passing to the agent: `re.sub(r"<@\w+>\s*", "", text).strip()`.
- **Rate limits.** Slack throttles per-channel posting (~1 msg/sec sustained). For escalation flows that batch reports, add backoff (`tenacity`). Bolt does not retry by default.
- **Block Kit for rich expert-channel messages.** Plain markdown works (`*bold*`, `_italic_`, `>quote`), but for structured escalation reports use `blocks=[...]` — clearer UX and easier to maintain than markdown templates.
- **Don't block the event handler.** Slack expects an ack within 3 seconds. Long agent runs (5-30s) must `ack()` immediately and reply asynchronously, or use Bolt's `lazy=` listeners.

## Source

Standard Slack Bolt patterns; not covered in lectures (this is project-specific to our Phase 5).
