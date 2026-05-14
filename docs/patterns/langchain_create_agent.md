# LangChain create_agent (1.x)

## When to use

When you need a ReAct-style agent that picks tools, runs them, observes results, and continues until done — wrapped as a single LangGraph node.

In this project: every worker (`Lawyer`, `Common Support`, `Technical Support`) is built with `create_agent`. Supervisor and Planner are *not* — they're explicit graph logic with single LLM calls.

## Minimal example

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web. Use for general information needs."""
    return f"results for {query}"

@tool
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base. Use for product/policy questions."""
    return f"kb results for {query}"

llm = init_chat_model("openai:gpt-4o", temperature=0)

researcher = create_agent(
    model=llm,
    tools=[web_search, search_knowledge_base],
    system_prompt=(
        "You are a researcher. Use the available tools to gather information. "
        "Call web_search for current external info, search_knowledge_base for product specifics. "
        "Be concise."
    ),
    name="researcher",
)

# `researcher` IS a compiled LangGraph — invoke directly or use as a node
result = researcher.invoke({"messages": [{"role": "user", "content": "What is LangGraph?"}]})
```

## Pitfalls

- **`create_agent` is from `langchain.agents` (1.x)**, not the older `langgraph.prebuilt.create_react_agent` from earlier examples. Pin versions to avoid mixing APIs.
- **The agent IS a graph** — its output shape is `MessagesState`-like (`{"messages": [...]}`). When using it as a node in a parent graph, decide whether the parent state should embed the agent's messages or just the final answer.
- **Tool docstrings are part of the prompt.** They tell the LLM *when* to use each tool. Vague docstring = wrong tool selection. Always describe trigger conditions, not just behavior.
- **`name` matters in multi-agent systems** — Supervisor's structured output references workers by name, and tracing UIs (Langfuse) display this name.
- **Structured final output:** add `response_format=SchemaModel` to make the agent return a typed result instead of a free-text message. The agent's last step becomes a structured-output call. Required for `WorkerResponse` in our project.
- **Middleware** (`HumanInTheLoopMiddleware`, `SummarizationMiddleware`) attaches via the `middleware=[...]` parameter — see `langchain_hitl_middleware.md`.

## Source

`lesson-7.md` (cells 24 — researcher/writer agents); `lesson-8.md` (cells 28-30 — calendar/email/research agents with prompts).
