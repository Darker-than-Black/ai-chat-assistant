# LangChain HumanInTheLoopMiddleware

## When to use

When specific tool calls need human approval before execution. Pauses the agent at the tool-call boundary, persists state via the checkpointer, and waits for an `approve` / `reject` / `edit` decision.

In this project: **not used** in the current scope (escalation goes via static message + Slack post, no interactive approval). Listed here as a reference for future "approve before publishing to expert channel" or similar gates — and because it's the canonical pattern in the lecture material.

## Minimal example

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver  # or PostgresSaver

calendar_agent = create_agent(
    model=llm,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt="You are a calendar assistant.",
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "create_calendar_event": True,        # write op — needs approval
                "get_available_time_slots": False,    # read op — auto-approved
            },
            description_prefix="📅 Calendar event pending approval",
        ),
    ],
)

# A checkpointer is REQUIRED for HITL — the interrupt persists state.
app = calendar_agent  # already compiled with the middleware

# First call interrupts before create_calendar_event
result = app.invoke({"messages": [...]}, config={"configurable": {"thread_id": "t1"}})
# result contains an Interrupt object

# Resume with a decision
from langgraph.types import Command
result = app.invoke(
    Command(resume={"action": "approve"}),
    config={"configurable": {"thread_id": "t1"}},
)
```

## Pitfalls

- **Requires a checkpointer.** Without it, the interrupt has nowhere to persist state. Use `PostgresSaver` for production (see `langgraph_postgres_checkpointer.md`).
- **Read vs write rule.** Set `False` (auto-approve) for read-only tools, `True` (or a decision dict) for tools that mutate external state. Wrong classification = either UX hell (approving every search) or unsafe (auto-approving sends).
- **Resume contract:** the resume value must match what the middleware expects. With `interrupt_on={"tool": True}` it accepts `{"action": "approve" | "reject"}`. With richer config (`{"allowed_decisions": [...]}`) the schema differs — read the middleware's signature.
- **`thread_id` must be the same** across invoke + resume. New `thread_id` = the agent doesn't know about the interrupted call.
- **Don't bypass the middleware** by calling the tool directly elsewhere. The whole point is that *all* paths to the tool go through the gate.

## Source

`lesson-8.md` (cells 45-47 — HITL on calendar/email agents).
