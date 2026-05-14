# LangGraph dynamic fan-out with Send API

## When to use

When the **number of parallel branches is not known at graph-compile time** and depends on runtime data. Static parallelism (e.g. fixed `[A, B, C]` siblings) doesn't need `Send`.

In this project: `Planner` returns a variable list of `SubTask`s; the supervisor must dispatch each subtask to the matching worker (legal → Lawyer, technical → Technical Support, etc.) — possibly 1, 2 or 3 simultaneous workers per request.

## Minimal example

```python
from langgraph.types import Send
from typing import TypedDict, Annotated
from operator import add

class State(TypedDict):
    subtasks: list[dict]                          # produced by an upstream planner node
    worker_responses: Annotated[list[dict], add]  # MUST use a reducer

# Router returning Send objects = dynamic fan-out
def fan_out(state: State) -> list[Send]:
    return [
        Send(_node_for(task["topic"]), {"subtask": task})
        for task in state["subtasks"]
    ]

def _node_for(topic: str) -> str:
    return {"legal": "lawyer", "technical": "technical_support", "general": "common_support"}[topic]

# Each Send launches the target node with its own input dict.
# The reducer on `worker_responses` accumulates outputs from all branches.
graph.add_conditional_edges("planner", fan_out, ["lawyer", "technical_support", "common_support"])
```

Each worker node receives `{"subtask": ...}` — the input you put in the `Send(node, input)` call. It does **not** see the full state by default. Return a delta containing `worker_responses` and the reducer accumulates.

## Pitfalls

- **The target field MUST have a reducer** (`Annotated[list, add]`). Without it, parallel writes overwrite each other and only the last branch's output survives.
- **Each `Send` runs in isolation** — the input dict you pass is the *entire* state visible to that branch's node. Pass everything the worker needs (subtask + session_id + any flags).
- **Branches converge automatically** at the next node. The downstream node sees the merged state with all branch outputs.
- **`add_conditional_edges`** still needs a list of possible target nodes (third arg) for graph visualization and validation — even though the router returns `Send` objects, list every node that *could* be a target.
- **`Send` skips conditional edges entirely** — it goes straight to the named node. Conditional logic per branch must be inside the worker itself.
- **Targeted re-dispatch** (in our Critic loop): same pattern, but only for nodes named in `revision_requests` — not all workers.

## Source

`lesson-7.md` (cells 23, 56 — Send + Annotated reducer); concept primer around line 444.
