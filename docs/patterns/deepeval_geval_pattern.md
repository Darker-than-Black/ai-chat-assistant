# DeepEval: GEval and Tool Correctness

## When to use

Component and end-to-end testing of agents. Two key metric types we use:

- **`GEval`** — write your own quality criteria as `evaluation_steps` and let an LLM judge.
- **`ToolCorrectnessMetric`** — verify the agent picks the right tools (and right args) for a query.

In this project: every component test in `tests/test_*.py`. End-to-end tests use `GEval` for `Correctness` against `expected_output`, plus `AnswerRelevancyMetric` (built-in, referenceless).

## Minimal example — GEval

```python
from deepeval import evaluate
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

# Custom metric: groundedness in retrieval context
groundedness = GEval(
    name="Groundedness",
    evaluation_steps=[
        "Extract every factual claim from 'actual output'",
        "For each claim, check if it can be directly supported by 'retrieval context'",
        "Claims not present in retrieval context count as ungrounded, even if true",
        "Score = number of grounded claims / total claims",
    ],
    evaluation_params=[
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.RETRIEVAL_CONTEXT,
    ],
    model="gpt-4o-mini",
    threshold=0.7,
)

test_case = LLMTestCase(
    input="What is the fine for procurement violations under article 164-14?",
    actual_output="The fine ranges from 1500 to 3000 non-taxable minimums for officials.",
    retrieval_context=["...text from KUpAP article 164-14..."],
)

evaluate(test_cases=[test_case], metrics=[groundedness])
```

## Minimal example — ToolCorrectness

```python
from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams
from deepeval.metrics import ToolCorrectnessMetric

tools_called = [
    ToolCall(name="rag_search", input_parameters={"query": "стаття 164-14", "collection": "laws"},
             output="..."),
]
expected_tools = [
    ToolCall(name="rag_search", input_parameters={"query": "стаття 164-14", "collection": "laws"},
             output="..."),
]

test_case = LLMTestCase(
    input="What does article 164-14 say about procurement violations?",
    actual_output="...",
    tools_called=tools_called,
    expected_tools=expected_tools,
)

# Basic — just check tool names match
basic = ToolCorrectnessMetric(threshold=0.5, model="gpt-4o-mini")

# Strict — check params and exact sequence
strict = ToolCorrectnessMetric(
    threshold=0.5,
    evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
    should_exact_match=True,
    model="gpt-4o-mini",
)
```

## Pitfalls

- **`evaluation_params` must contain only what you reference in `evaluation_steps`.** Including `EXPECTED_OUTPUT` when steps don't mention it confuses the judge and inflates token cost.
- **`evaluation_steps` are the prompt.** Each step is read by the judge LLM verbatim. Vague steps → noisy scores. Be specific (e.g. *"Extract every factual claim"* beats *"Check if it's correct"*).
- **`criteria` (string) vs `evaluation_steps` (list).** Use one or the other. `evaluation_steps` gives more control and is preferred for component tests.
- **Threshold is your business decision.** Don't start at 0.95 — establish baseline scores first, raise the bar over time.
- **`ToolCorrectnessMetric` defaults to checking only tool names.** Add `evaluation_params=[ToolCallParams.INPUT_PARAMETERS]` to also verify args. Add `should_exact_match=True` to enforce the exact sequence (no extra steps allowed).
- **Tool outputs in test cases:** match the format your real tools produce. Otherwise `ToolCorrectnessMetric`'s strict mode flags innocent diffs.
- **Cost.** Each metric call = at least one judge LLM invocation. A 20-case dataset × 4 metrics = 80 LLM calls. Use `gpt-4o-mini` as the judge model for cost control; reserve `gpt-4o` for high-stakes correctness checks.
- **`evaluate()` blocks** until all judge calls complete. For large suites, use DeepEval's async/parallel modes.

## Source

`lesson-10.md` (cell 17 — basic AnswerRelevancy + GEval Correctness; cell 23 — ToolCorrectness with ToolCall + expected_tools).
