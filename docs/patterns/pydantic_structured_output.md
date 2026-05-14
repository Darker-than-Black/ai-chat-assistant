# Pydantic structured output

## When to use

Whenever an LLM call needs a typed result instead of free text — agent decisions, plan generation, classification, critique verdicts. Replaces manual JSON parsing entirely.

In this project: every inter-agent contract (`ResearchPlan`, `WorkerResponse`, `CritiqueResult`, `EscalationOutput`) is produced via `with_structured_output`. Never hand-parse JSON from `.content`.

## Minimal example

```python
from pydantic import BaseModel
from typing import Literal
from langchain_openai import ChatOpenAI

class Router(BaseModel):
    """Supervisor routing decision."""
    next: Literal["researcher", "writer", "FINISH"]
    reasoning: str

llm = ChatOpenAI(model="gpt-4o", temperature=0)

response = llm.with_structured_output(Router).invoke([
    {"role": "system", "content": "Route to researcher or writer. Say FINISH when done."},
    {"role": "user", "content": "Research multi-agent systems and write a summary."},
])

# response is a typed Router instance
print(response.next)        # "researcher"
print(response.reasoning)   # str
```

## Pitfalls

- **Schema is sent to the model.** Field descriptions (`Field(description=...)`) and the model's docstring are part of the prompt — write them carefully, they're not "just for IDE".
- **`Literal` types prevent invented categories.** Always prefer `Literal[...]` over `str` for enums; the model can't return values outside the set.
- **Optional fields need defaults.** `field: str | None = None` — without the default, validation fails when the model omits it.
- **Cross-field constraints belong in `model_validator`** (see `pydantic_validators.md`), not in the schema description.
- **Provider differences:** OpenAI uses native function-calling; Anthropic uses tool-calling under the hood. Both work via the same `with_structured_output` API, but if you bind tools elsewhere on the same model, conflicts can occur — call `with_structured_output` on a fresh `llm` instance.

## Source

`lesson-7.md` (cells 21, 24 — Plan/Review/Router models).
