# LangGraph conditional edges

## When to use

Whenever a node's outcome determines which node runs next — routing, decision branching, retry-vs-end logic.

In this project: after `planner` (off-topic / escalation / fan-out), after `critic` (approve / revise / give-up).

## Minimal example

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

def route_after_classify(state) -> Literal["billing", "technical", "general"]:
    return state["category"]

graph = StateGraph(SupportState)
graph.add_node("classify", classify)
graph.add_node("billing", billing_agent)
graph.add_node("technical", technical_agent)
graph.add_node("general", general_agent)

graph.add_edge(START, "classify")
graph.add_conditional_edges(
    "classify",
    route_after_classify,
    {"billing": "billing", "technical": "technical", "general": "general"},
)
```

The router function is **pure** — it reads state and returns a key (or list of keys for parallel dispatch). It does *not* mutate state. State updates belong in nodes.

## Pitfalls

- **The mapping dict is required** (third argument). Without it, the return value of the router must literally be a node name. With the mapping, the router can return any sentinel and the dict translates it.
- **Returning a value not in the mapping** raises at runtime, not at compile time. Always include `END` if the router can decide to terminate.
- **Routing to multiple nodes is allowed** — return a `list[str]` and the graph runs them in parallel. For dynamic fan-out (data-dependent), use `Send` API instead — see `langgraph_fanout_with_send.md`.
- **Don't put long logic in the router.** Heavy work (LLM calls, tool calls) goes in nodes. Routers should be cheap and deterministic.
- **`Command`** is an alternative pattern: a node returns `Command(goto=..., update=...)` to update state and route in one step. Useful when the routing decision depends on the LLM call inside the node itself.

## Source

`lesson-6.md` (cell 14, lines 286-294 — classify → routes); `lesson-7.md` (cell 24 — `Command` API as alternative).
