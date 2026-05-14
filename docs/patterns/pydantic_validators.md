# Pydantic cross-field validators

## When to use

When a Pydantic model has **invariants between fields** that the schema alone can't express:

- *"if `is_on_topic=False` → `subtasks` must be empty"*
- *"if `verdict='revise'` → `revision_requests` must be non-empty"*
- *"if `needs_human=True` → `escalation_reason` must be set"*

These are exactly the rules our agent contracts enforce (`ResearchPlan`, `CritiqueResult`).

## Minimal example

```python
from pydantic import BaseModel, model_validator
from typing import Literal

class CritiqueResult(BaseModel):
    verdict: Literal["approve", "revise"]
    revision_requests: list[str] = []

    @model_validator(mode="after")
    def revise_requires_requests(self):
        if self.verdict == "revise" and not self.revision_requests:
            raise ValueError("verdict='revise' requires non-empty revision_requests")
        if self.verdict == "approve" and self.revision_requests:
            raise ValueError("verdict='approve' must have empty revision_requests")
        return self
```

`mode="after"` runs *after* individual fields are parsed and validated, so `self` already has typed attributes. Always `return self` at the end.

## Pitfalls

- **Validators run when the LLM returns the structured output too.** If a validator raises, `with_structured_output` will surface that error — wrap LLM calls expecting potential validation failures with a retry layer if needed.
- **Don't mutate `self` in validators** unless intentional. Use them for *checking*, not *fixing*.
- **`mode="before"`** receives raw input dict (use only for normalization, e.g. lowercasing); **`mode="after"`** receives parsed model. Default to `"after"`.
- **Multiple validators are chained** in declaration order. If the first raises, later ones don't run — useful for layered checks.
- For per-field validation use `field_validator` instead — `model_validator` is for cross-field rules.

## Source

Pattern is standard Pydantic 2.x; cross-field invariants for our schemas come from `ARCHITECTURE.md § 4`.
