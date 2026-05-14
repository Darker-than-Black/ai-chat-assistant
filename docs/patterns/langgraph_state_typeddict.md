# LangGraph state with TypedDict and reducers

## When to use

Defining the shared state object for any `StateGraph`. State is the "blackboard" — every node reads from and writes to it.

Two cases need reducers (`Annotated[T, reducer_fn]`):
- **List accumulation** when multiple nodes (or a fan-out) append to the same field. Without a reducer, each write *replaces* the previous value.
- **Custom merge logic** for dicts, sets, or domain-specific types.

In this project: `worker_responses` from parallel workers must accumulate, not overwrite — see `langgraph_fanout_with_send.md`.

## Minimal example

```python
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AnyMessage

class GraphState(TypedDict):
    user_message: str                        # plain field — overwritten on each write
    messages: Annotated[list[AnyMessage], add]  # list — appended via operator.add
    retry_count: int                         # plain int — last write wins

graph = StateGraph(GraphState)
graph.add_node("step", lambda s: {"messages": [AIMessage("hi")], "retry_count": s["retry_count"] + 1})
graph.add_edge(START, "step")
graph.add_edge("step", END)

app = graph.compile()
result = app.invoke({"user_message": "hello", "messages": [], "retry_count": 0})
```

For pre-built message handling LangGraph also offers `MessagesState` — a TypedDict with `messages: Annotated[list, add_messages]` already wired (the `add_messages` reducer also dedups by `id`).

## Pitfalls

- **Returning unknown keys is silently ignored.** State schema is the contract — typo in a field name = lost data with no error.
- **Reducer applies on the value the node returns**, not on `state[field]`. A node returning `{"messages": [m1]}` triggers `add(state["messages"], [m1])`. Returning `{"messages": state["messages"] + [m1]}` will *double* the existing items.
- **Don't share mutable defaults between runs.** TypedDict doesn't enforce immutability; treat state as read-only inside nodes, return only the *delta*.
- **`operator.add` works for lists, strings, numbers** — but for dicts you need a custom reducer (`lambda a, b: {**a, **b}` or stricter merge logic).

## Source

`lesson-6.md` (cell 14 — SupportState), conceptual breakdown around line 380-400.
