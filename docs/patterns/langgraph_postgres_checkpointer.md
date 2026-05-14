# LangGraph Postgres checkpointer

## When to use

For **persistent sessions** — the agent must survive process restarts and remember the conversation across runs. Required for any production deployment with multi-turn dialogues.

In this project: Slack bot users expect their context to persist across days; `MemorySaver` (in-memory) is for unit tests only.

## Minimal example

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph

POSTGRES_URL = "postgresql://user:pass@localhost:5432/agents"

# One-time schema setup — idempotent, run on first start or via migration script
with PostgresSaver.from_conn_string(POSTGRES_URL) as checkpointer:
    checkpointer.setup()

# Production usage — long-lived connection
checkpointer = PostgresSaver.from_conn_string(POSTGRES_URL).__enter__()
app = graph.compile(checkpointer=checkpointer)

# Each invocation needs a thread_id to scope the conversation
config = {"configurable": {"thread_id": "team:channel:user"}}
result = app.invoke({"user_message": "hi"}, config=config)

# Subsequent calls with the same thread_id resume the conversation
result2 = app.invoke({"user_message": "follow-up"}, config=config)
```

`thread_id` format in this project: `team_id:channel_id:user_id[:thread_ts]` — see `CLAUDE.md` "Sessions" invariant.

## Pitfalls

- **`setup()` must be called once** before first use. It creates the `checkpoints` and `checkpoint_writes` tables. Idempotent — safe to call repeatedly. Standard practice: a separate `scripts/setup_postgres_checkpointer.py` that's run during deployment.
- **Connection lifecycle:** `from_conn_string` returns a context manager. In long-running services, enter the context once at startup and keep it for the process lifetime. Don't open/close per request.
- **`thread_id` must be deterministic and stable** for the same logical conversation. If you regenerate it (e.g. UUIDs), each request looks like a new session and history is lost.
- **Checkpointing ≠ durable execution.** If the process crashes mid-graph, you must manually call `app.invoke(None, config=config)` with the same `thread_id` to resume — there's no automatic retry.
- **Schema changes between LangGraph versions** can require a re-run of `setup()` after upgrades. Pin the version in `requirements.txt`.
- **`MemorySaver` for tests is fine**, but it does *not* implement the same interface as `PostgresSaver` for advanced features (state history queries). Test-specific differences are acceptable here.

## Source

`lesson-11.md` (cells around line 460 — Dev vs Production checkpointers). Setup pattern is standard from `langgraph-checkpoint-postgres` package.
