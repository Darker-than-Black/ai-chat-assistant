# Plan: Phase 5 — Sessions + Slack Integration

## Task Description

Migrate the system from an in-memory checkpointer and CLI-only REPL to a production-ready Slack bot with persistent sessions backed by PostgreSQL. Covers five checklist items (5.1–5.5):

- **5.1** Replace `MemorySaver` with `PostgresSaver` for persistent sessions
- **5.2** Implement `make_session_id()` helper (format: `team_id:channel_id:user_id[:thread_ts]`)
- **5.3** Add Slack Bolt `app_mention` handler with in-thread replies
- **5.4** Create `tools/slack_publisher.py` for expert-channel escalation notifications
- **5.5** Add `--mode=slack|repl` flag so REPL still works for dev/demo

## Objective

After this phase `python main.py --mode=slack` starts a Socket Mode Slack bot that responds to `@mentions` in the user channel with in-thread replies, uses persistent Postgres sessions (conversation history survives restarts), and posts Block Kit escalation notices to the expert channel with file fallback. `python main.py` (default REPL) continues to work unchanged.

## Problem Statement

The current system has two gaps that prevent any real deployment:
1. **No persistence** — `MemorySaver` is wiped on every restart; sessions are per-process UUIDs, not user-scoped identifiers.
2. **No Slack surface** — users must shell into the CLI; there is no way to expose the system to non-technical procurement staff.

## Solution Approach

The checkpointer concern and the Slack concern are architecturally independent and can be addressed in a single phase. The key insight is to keep `supervisor.build_graph()` defaulting to `MemorySaver` (so all existing tests keep working without a Postgres connection) while production `main.py` creates a `PostgresSaver` at startup and passes it in explicitly.

### Architecture Decisions

- **Affected graph nodes**: None. Phase 5 is infrastructure (entry point + checkpointer). No agent logic changes.
- **Schemas**: `EscalationOutput` used as-is (current 4-field version). Phase 6 expands it; Phase 5's publisher adapts to whatever fields are present.
- **RAG collections**: Not touched.
- **External calls**:
  - `PostgresSaver` — long-lived connection held for process lifetime (pattern file § "Connection lifecycle").
  - Slack `App` + `SocketModeHandler` — two tokens: `SLACK_BOT_TOKEN` (xoxb-) and `SLACK_APP_TOKEN` (xapp-).
  - `slack_sdk.WebClient` (standalone, inside `tools/slack_publisher.py`) — separate from the Bolt `App`, so it can be called from escalation logic in Phase 6 without importing the whole Bolt app.
- **Sessions / persistence**: `PostgresSaver.from_conn_string().__enter__()` called once at startup; thread ID format `team_id:channel_id:user_id:thread_ts` (always include `thread_ts` for Slack — keeps threads isolated).
- **Prompt source**: Not affected.
- **Slack ack**: `App(process_before_response=True)` — Bolt handles the 3-second ack automatically while the handler runs on a worker thread. Simpler than `lazy=` for synchronous handlers.

## Relevant Files

### Modified
- `config.py` — add `slack_app_token: SecretStr | None = None` (Socket Mode requires a second token)
- `supervisor.py` — change `build_graph()` to accept optional `checkpointer` param; module-level `graph = build_graph()` keeps `MemorySaver` for test imports
- `main.py` — add argparse `--mode`, extract `_run_repl()` / `_run_slack()`, add `make_session_id()`, accept `user_id` in `build_initial_state()`, init PostgresSaver in production path
- `.env.example` — add `SLACK_APP_TOKEN=xapp-***`

### New Files
- `tools/slack_publisher.py` — `post_to_expert_channel(EscalationOutput)` with Block Kit formatting and file fallback
- `tests/test_session_id.py` — unit tests for `make_session_id`
- `tests/test_slack_publisher.py` — unit tests for publisher (mocked `WebClient`, file fallback path)

## Implementation Phases

- [ ] **Phase 1: Foundation** — Config + supervisor parameterization
  - Status:
  - Comments:

- [ ] **Phase 2: Core Implementation** — main.py refactor + slack_publisher
  - Status:
  - Comments:

- [ ] **Phase 3: Tests + Validation** — test coverage + smoke test
  - Status:
  - Comments:

## Step by Step Tasks

### 1. Config: add SLACK_APP_TOKEN

- [ ] **Add `slack_app_token` field to Settings** — insert below `slack_signing_secret` in `config.py`: `slack_app_token: SecretStr | None = None`
  - Status:
  - Comments:

- [ ] **Update `.env.example`** — add `SLACK_APP_TOKEN=xapp-***` below `SLACK_SIGNING_SECRET` with comment `# xapp-... required ONLY for Socket Mode (not HTTP mode)`
  - Status:
  - Comments:

### 2. Supervisor: parameterize checkpointer

- [ ] **Change `build_graph()` signature** — replace the hardcoded `MemorySaver()` argument in `builder.compile()` with an injected checkpointer:
  ```python
  from langgraph.checkpoint.memory import MemorySaver

  def build_graph(checkpointer=None):
      builder = StateGraph(GraphState)
      # ... (all node/edge wiring unchanged) ...
      return builder.compile(checkpointer=checkpointer if checkpointer is not None else MemorySaver())

  graph = build_graph()  # MemorySaver — used by test imports
  ```
  - Status:
  - Comments: The module-level `graph` keeps `MemorySaver` so `from supervisor import graph` in tests continues to work without a Postgres connection. Production `main.py` passes its own `PostgresSaver` instance.

### 3. main.py: make_session_id helper

- [ ] **Add `make_session_id()` function** — place it at the top of `main.py` (before `build_initial_state`):
  ```python
  def make_session_id(team_id: str, channel_id: str, user_id: str, thread_ts: str | None = None) -> str:
      base = f"{team_id}:{channel_id}:{user_id}"
      return f"{base}:{thread_ts}" if thread_ts else base
  ```
  - Status:
  - Comments:

### 4. main.py: fix build_initial_state user_id param

- [ ] **Add `user_id` parameter** — change the signature and body:
  ```python
  def build_initial_state(user_message: str, session_id: str, user_id: str = "cli-user") -> GraphState:
      return {
          "user_message": sanitize_terminal_text(user_message),
          "session_id": session_id,
          "user_id": user_id,
          ...
      }
  ```
  - Status:
  - Comments: Default `"cli-user"` preserves REPL behaviour; Slack path passes the actual Slack `user_id`.

### 5. main.py: extract _run_repl() and wire PostgresSaver

- [ ] **Refactor main REPL into `_run_repl(graph)`** — extract the while-loop from the current `main()` into a standalone function that accepts the graph as a parameter:
  ```python
  def _run_repl(graph) -> None:
      print(f"Prozorro Assistant  [{settings.llm_provider}/{settings.llm_model}]")
      print("Введіть запитання або 'exit' для виходу.\n")
      while True:
          try:
              user_input = input("Запит: ").strip()
          except (EOFError, KeyboardInterrupt):
              print("\nДо побачення!")
              break
          if not user_input:
              continue
          if user_input.lower() in ("exit", "quit"):
              print("До побачення!")
              break

          session_id = make_session_id("cli", "cli", "cli-user")
          initial_state = build_initial_state(user_input, session_id)
          result = graph.invoke(
              initial_state,
              {"configurable": {"thread_id": session_id}},
          )
          print(f"\n{result['final_response']}")
          if result.get("escalated"):
              print("Запит позначено для подальшого опрацювання фахівцем.")
          print()
  ```
  Note: REPL uses a stable deterministic session ID so the same CLI session accumulates context within a single run, consistent with the intent of the checkpointer.
  - Status:
  - Comments:

- [ ] **Add `_build_postgres_graph()` factory** — creates the PostgresSaver-backed graph for production:
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver
  from supervisor import build_graph

  def _build_postgres_graph():
      checkpointer = PostgresSaver.from_conn_string(settings.postgres_url).__enter__()
      checkpointer.setup()
      return build_graph(checkpointer=checkpointer)
  ```
  - Status:
  - Comments: `__enter__()` keeps the connection alive for the process lifetime (per `langgraph_postgres_checkpointer.md` pattern). `setup()` is idempotent — safe to call on every startup.

### 6. main.py: add _run_slack() and argparse

- [ ] **Add `_run_slack(graph)` function**:
  ```python
  import re
  from slack_bolt import App
  from slack_bolt.adapter.socket_mode import SocketModeHandler

  def _run_slack(graph) -> None:
      assert settings.slack_bot_token, "SLACK_BOT_TOKEN required for Slack mode"
      assert settings.slack_signing_secret, "SLACK_SIGNING_SECRET required for Slack mode"
      assert settings.slack_app_token, "SLACK_APP_TOKEN (xapp-...) required for Socket Mode"

      app = App(
          token=settings.slack_bot_token.get_secret_value(),
          signing_secret=settings.slack_signing_secret.get_secret_value(),
          process_before_response=True,
      )

      @app.event("app_mention")
      def handle_mention(event, say):
          user_id = event["user"]
          channel_id = event["channel"]
          team_id = event.get("team", "unknown")
          thread_ts = event.get("thread_ts") or event["ts"]

          raw_text = event["text"]
          user_text = re.sub(r"<@\w+>\s*", "", raw_text).strip()
          if not user_text:
              say(text="Будь ласка, введіть запит.", thread_ts=thread_ts)
              return

          session_id = make_session_id(team_id, channel_id, user_id, thread_ts)
          initial_state = build_initial_state(user_text, session_id, user_id)
          result = graph.invoke(
              initial_state,
              {"configurable": {"thread_id": session_id}},
          )
          say(text=result["final_response"], thread_ts=thread_ts)

      SocketModeHandler(app, settings.slack_app_token.get_secret_value()).start()
  ```
  - Status:
  - Comments: `process_before_response=True` delegates the WebSocket ack to a background thread, so the 3-second deadline does not apply to the handler body. `re.sub` strips `<@U123>` mention prefix. Always reply in thread via `thread_ts`.

- [ ] **Rewrite `main()` with argparse**:
  ```python
  import argparse

  def main() -> None:
      parser = argparse.ArgumentParser(description="Prozorro Support Assistant")
      parser.add_argument("--mode", choices=["repl", "slack"], default="repl")
      args = parser.parse_args()

      if args.mode == "slack":
          graph = _build_postgres_graph()
          _run_slack(graph)
      else:
          graph = _build_postgres_graph()
          _run_repl(graph)
  ```
  - Status:
  - Comments: Both modes use PostgresSaver. REPL mode can still be used for manual testing against the real DB. If Postgres is unavailable during dev, run tests via pytest (which use MemorySaver).

- [ ] **Remove the `from supervisor import graph` import** in `main.py` — replace with `from supervisor import build_graph`
  - Status:
  - Comments:

### 7. tools/slack_publisher.py — create expert-channel publisher

- [ ] **Create `tools/slack_publisher.py`** with the following structure:
  ```python
  """Expert-channel Slack publisher for escalation notifications.

  Uses standalone WebClient (not Bolt App) so it can be called from
  escalation logic (Phase 6) without importing the full Slack Bolt runtime.
  Falls back to a local JSON file when Slack is unavailable.
  """

  import json
  from datetime import datetime
  from pathlib import Path

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
      """Publish escalation to expert Slack channel; write to file as fallback."""
      assert settings.slack_expert_channel_id, "SLACK_EXPERT_CHANNEL_ID is required"
      message = _build_message(escalation)
      try:
          _get_client().chat_postMessage(
              channel=settings.slack_expert_channel_id,
              text=message["text"],
              blocks=message["blocks"],
          )
      except (SlackApiError, AssertionError) as exc:
          _save_to_file(escalation, error=str(exc))


  def _build_message(escalation: EscalationOutput) -> dict:
      """Build Block Kit payload following ARCHITECTURE § 9.3."""
      return {
          "text": f"Ескалація: {escalation.reason}",
          "blocks": [
              {
                  "type": "header",
                  "text": {"type": "plain_text", "text": "🚨 Ескалація запиту"},
              },
              {
                  "type": "section",
                  "fields": [
                      {"type": "mrkdwn", "text": f"*Сесія:*\n`{escalation.session_id}`"},
                      {"type": "mrkdwn", "text": f"*Час:*\n{escalation.timestamp}"},
                  ],
              },
              {
                  "type": "section",
                  "text": {
                      "type": "mrkdwn",
                      "text": f"*Запит користувача:*\n{escalation.original_query}",
                  },
              },
              {
                  "type": "section",
                  "text": {
                      "type": "mrkdwn",
                      "text": f"*Причина ескалації:*\n{escalation.reason}",
                  },
              },
          ],
      }


  def _save_to_file(escalation: EscalationOutput, error: str = "") -> None:
      output_dir = Path("output/escalations")
      output_dir.mkdir(parents=True, exist_ok=True)
      safe_session = escalation.session_id.replace(":", "_")
      safe_ts = escalation.timestamp.replace(":", "-")
      path = output_dir / f"{safe_session}_{safe_ts}.json"
      with open(path, "w", encoding="utf-8") as f:
          json.dump(
              {"escalation": escalation.model_dump(), "slack_error": error},
              f,
              ensure_ascii=False,
              indent=2,
          )
  ```
  - Status:
  - Comments: Phase 6 will call `post_to_expert_channel` from the real escalation node. In Phase 5, the function is fully usable but only wired to the graph in Phase 6. The file fallback always writes `output/escalations/` regardless of Slack state — that directory is the audit trail.

### 8. Tests: test_session_id.py

- [ ] **Create `tests/test_session_id.py`** with unit tests for `make_session_id`:
  ```python
  import pytest
  from main import make_session_id

  def test_without_thread_ts():
      result = make_session_id("T123", "C456", "U789")
      assert result == "T123:C456:U789"

  def test_with_thread_ts():
      result = make_session_id("T123", "C456", "U789", thread_ts="1234567890.000100")
      assert result == "T123:C456:U789:1234567890.000100"

  def test_empty_thread_ts_omitted():
      result = make_session_id("T123", "C456", "U789", thread_ts=None)
      assert ":" not in result[len("T123:C456:U789"):]

  def test_deterministic():
      a = make_session_id("T1", "C1", "U1", "ts1")
      b = make_session_id("T1", "C1", "U1", "ts1")
      assert a == b

  def test_different_threads_different_sessions():
      s1 = make_session_id("T1", "C1", "U1", "ts_a")
      s2 = make_session_id("T1", "C1", "U1", "ts_b")
      assert s1 != s2
  ```
  - Status:
  - Comments:

### 9. Tests: test_slack_publisher.py

- [ ] **Create `tests/test_slack_publisher.py`** with mocked WebClient tests:
  ```python
  import json
  from pathlib import Path
  from unittest.mock import MagicMock, patch

  import pytest
  from slack_sdk.errors import SlackApiError

  from schemas import EscalationOutput
  from tools.slack_publisher import _build_message, post_to_expert_channel

  SAMPLE = EscalationOutput(
      reason="Бот не зміг відповісти",
      original_query="Як скасувати тендер?",
      session_id="T1:C1:U1:ts1",
      timestamp="2026-05-03T10:00:00",
  )


  def test_build_message_structure():
      msg = _build_message(SAMPLE)
      assert "blocks" in msg
      assert "text" in msg
      assert any("Ескалація" in b.get("text", {}).get("text", "") for b in msg["blocks"])


  @patch("tools.slack_publisher._get_client")
  def test_post_calls_chat_post_message(mock_get_client, monkeypatch):
      monkeypatch.setattr("tools.slack_publisher.settings.slack_expert_channel_id", "C_EXPERT")
      mock_client = MagicMock()
      mock_get_client.return_value = mock_client

      post_to_expert_channel(SAMPLE)

      mock_client.chat_postMessage.assert_called_once()
      call_kwargs = mock_client.chat_postMessage.call_args.kwargs
      assert call_kwargs["channel"] == "C_EXPERT"


  @patch("tools.slack_publisher._get_client")
  def test_slack_error_writes_file(mock_get_client, monkeypatch, tmp_path):
      monkeypatch.setattr("tools.slack_publisher.settings.slack_expert_channel_id", "C_EXPERT")
      mock_client = MagicMock()
      mock_client.chat_postMessage.side_effect = SlackApiError("channel_not_found", {})
      mock_get_client.return_value = mock_client

      import tools.slack_publisher as pub
      original = pub._save_to_file
      saved = {}

      def fake_save(escalation, error=""):
          saved["escalation"] = escalation
          saved["error"] = error

      monkeypatch.setattr(pub, "_save_to_file", fake_save)
      post_to_expert_channel(SAMPLE)
      assert saved["escalation"] == SAMPLE
      assert "channel_not_found" in saved["error"]
  ```
  - Status:
  - Comments: Uses monkeypatch to avoid touching the filesystem. The `_build_message` test checks structural correctness without Slack credentials.

### 10. Validation and smoke test

- [ ] **Run full test suite** — confirm no regressions from supervisor.py refactor:
  ```bash
  pytest tests/ -q
  ```
  - Status:
  - Comments:

- [ ] **Syntax check all modified files**:
  ```bash
  python -m py_compile config.py supervisor.py main.py tools/slack_publisher.py
  ```
  - Status:
  - Comments:

- [ ] **Smoke-test REPL mode with Postgres** (requires `docker compose up -d` first):
  ```bash
  docker compose up -d
  python scripts/setup_postgres_checkpointer.py
  echo "Привіт, як зареєструватися на Prozorro?" | python main.py --mode=repl
  ```
  Verify that the second run with the same session_id picks up prior context (shows the checkpointer is working).
  - Status:
  - Comments:

## Testing Strategy

| Test file | What it tests | Mocking |
|---|---|---|
| `tests/test_session_id.py` | `make_session_id()` — format, determinism, thread isolation | None (pure function) |
| `tests/test_slack_publisher.py` | `post_to_expert_channel()` — happy path, Slack error → file fallback; `_build_message()` — Block Kit structure | `unittest.mock.patch` on `_get_client`, `monkeypatch` on `_save_to_file` |
| `tests/test_main.py` (existing) | `build_initial_state()` with new `user_id` param; argparse `--mode` routing | `monkeypatch` on `main.graph` (existing pattern) |
| `tests/test_graph_routing.py` (existing) | Graph routing — confirm `build_graph(checkpointer=MemorySaver())` still works | `monkeypatch.setattr` on supervisor node functions |

No integration tests for Slack events (would require a live Slack workspace). Session persistence is validated via the manual smoke test in Step 10.

## Acceptance Criteria

1. `python main.py` (or `--mode=repl`) runs the CLI REPL exactly as before.
2. `python main.py --mode=slack` starts a Slack Bolt Socket Mode app without errors (given valid tokens in `.env`).
3. `@mention` the bot in the user channel → bot replies in the same thread.
4. Session IDs follow the format `team_id:channel_id:user_id:thread_ts`.
5. Restarting `--mode=slack` and mentioning the bot in the same thread continues the same conversation (Postgres persistence).
6. `post_to_expert_channel(escalation)` sends a Block Kit message to the expert channel; when Slack API raises, a JSON file is created in `output/escalations/`.
7. All existing `pytest tests/ -q` tests pass without a Postgres connection.
8. `config.py` parses `SLACK_APP_TOKEN` and `.env.example` documents it.

## Validation Commands

```bash
# 1. Syntax check
python -m py_compile config.py supervisor.py main.py tools/slack_publisher.py

# 2. Unit tests (no infra needed)
pytest tests/test_session_id.py tests/test_slack_publisher.py -v

# 3. Full test suite — confirm no regressions
pytest tests/ -q

# 4. Postgres schema init (one-time, idempotent)
docker compose up -d
python scripts/setup_postgres_checkpointer.py

# 5. REPL smoke test with PostgresSaver
echo "Як зареєструватися на Prozorro?" | python main.py --mode=repl

# 6. Import check (graph + Slack publisher)
python -c "from supervisor import graph; print('graph OK:', type(graph))"
python -c "from tools.slack_publisher import post_to_expert_channel; print('publisher OK')"
```

## Notes

- **`slack-bolt` and `slack-sdk` are already in `requirements.txt`** — no new pip installs needed.
- **`psycopg[binary]` and `langgraph-checkpoint-postgres` are already pinned** in `requirements.txt`.
- **`SLACK_APP_TOKEN`** (`xapp-...`) is a different token from `SLACK_BOT_TOKEN` (`xoxb-...`). Obtain it from the Slack App dashboard → "Socket Mode" → "App-Level Tokens". Scope: `connections:write`.
- **Bot must be invited to both channels** (`/invite @bot-name`) before testing — Slack does not auto-add bots.
- **`agents/escalation.py` is not created here** — Phase 6 implements the full escalation agent. Phase 5 creates the publisher utility that Phase 6 will call.
- **`EscalationOutput` schema stays minimal** — Phase 5 uses the existing 4-field version. Phase 6 will expand it and `_build_message()` in `slack_publisher.py` will need a corresponding update.
- **REPL session ID**: uses `make_session_id("cli", "cli", "cli-user")` → `"cli:cli:cli-user"` — deterministic across restarts, so the REPL also benefits from Postgres persistence.
- **Deduplication bug in `final_response_node`** (noted in `app_review/review_20260503T203623Z.md` as HIGH-risk): duplicate `worker_responses` after critic revisions. This is a Phase 3 bug, out of scope here. Track separately.