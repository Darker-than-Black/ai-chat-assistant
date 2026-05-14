# Langfuse integration

## When to use

For tracing, prompt management, and online evaluation in production agent systems. Three concerns, one platform:

1. **Tracing** — every LLM call, tool call, and sub-agent in one nested trace.
2. **Prompt Management** — prompts versioned in the UI, loaded from the SDK by name + label.
3. **LLM-as-a-Judge** — evaluators run automatically on new traces.

In this project: mandatory in Phase 7. Replaces hardcoded prompts with Langfuse-managed ones; replaces ad-hoc `print` debugging with proper traces.

## Minimal example — tracing + sessions

```python
import uuid
from langchain_core.runnables import RunnableConfig
from langfuse import observe, propagate_attributes, get_client
from langfuse.langchain import CallbackHandler

langfuse = get_client()                          # reads LANGFUSE_* env vars
langfuse_handler = CallbackHandler()             # LangChain/LangGraph callback

SESSION_ID = f"team:channel:user-{uuid.uuid4().hex[:8]}"

@observe(name="agent-run")
def run_graph(user_message: str) -> dict:
    # Session/user/tags propagate to ALL nested spans (LLM calls, tools, sub-agents)
    with propagate_attributes(
        session_id=SESSION_ID,
        user_id="user_123",
        tags=["procurement-support", "production"],
        metadata={"phase": "p1.6", "experiment": "baseline"},
    ):
        return app.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=RunnableConfig(callbacks=[langfuse_handler]),
        )

result = run_graph("Compare open and simplified procurement")
langfuse.flush()    # ensure async spans are sent before process exit
```

## Minimal example — prompt management

```python
from langfuse import get_client

langfuse = get_client()

# Load by name + label. Labels are mutable pointers ("production", "staging").
prompt = langfuse.get_prompt("procurement-planner", label="production")

# Compile with template variables (Mustache-style {{var}})
system_message = prompt.compile(
    user_query=user_query,
    language="uk",
)

# Use as system prompt in your LLM call. Changing the `production` label in
# Langfuse UI takes effect on the NEXT call — no redeploy.
```

## Pitfalls

- **`flush()` before exit.** Langfuse sends spans asynchronously. Short-lived processes (REPL, scripts) must call `langfuse.flush()` or traces are lost.
- **`propagate_attributes` requires `@observe`** (or another active span) on the outer scope. Calling it without an active trace silently does nothing.
- **`CallbackHandler` reads env vars on init.** If you change `LANGFUSE_HOST` mid-process (rare, but happens in tests), recreate the handler.
- **Prompt compile uses `{{variable}}` syntax** (Mustache-like), not Python f-strings. Don't write `{var}` — it won't substitute.
- **Labels are NOT versions.** A label is a movable pointer. To pin a specific version, use `version=N` instead of `label=...`. Production typically uses labels for hot-swap; tests pin versions for reproducibility.
- **Score types matter for LLM-as-a-Judge.** Numeric (0-1), boolean, or categorical — pick consistently across evaluators or aggregate dashboards become messy.
- **Sessions group traces; users group sessions.** Setting `session_id` per request but not `user_id` makes user-level analytics impossible. Set both.
- **`@observe` on a function not called inside a Langfuse-managed scope creates a top-level trace.** That's correct for entry points (REPL handler, Slack handler) but wrong if the function is called inside another `@observe` — you'd get two top-level traces instead of nesting.

## Source

`lesson-12.md` (cells 14-15 — `CallbackHandler` + `propagate_attributes`; cell 21 — `get_prompt` / `compile`).
