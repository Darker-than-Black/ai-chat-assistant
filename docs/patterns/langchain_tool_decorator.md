# LangChain @tool decorator

## When to use

Defining functions an agent can call. Replaces hand-rolled JSON schemas — the decorator infers the schema from type hints and uses the docstring as the tool description.

In this project: all of `web_search`, `read_url`, `rag_search`, `slack_publish`, `save_escalation_report`. Plus thin wrappers around external APIs.

## Minimal example

```python
from langchain_core.tools import tool

@tool
def search_knowledge_base(query: str, collection: str = "articles") -> str:
    """Search the internal knowledge base.

    Use this for questions about product behavior, FAQs, tutorials,
    and policy documents. The `collection` argument selects the index:
    'laws' for legal patterns, 'articles' for everything else.
    """
    # ... implementation
    return formatted_results
```

The agent's LLM sees:
- Tool name: `search_knowledge_base`
- Description: the docstring (verbatim)
- Schema: derived from type hints — `{"query": str (required), "collection": str (default: "articles")}`

## Pitfalls

- **Docstring = prompt.** Spend real effort on it. Bad docstrings cause: wrong tool selection, wrong arguments, hallucinated results. Include *when* to use it, not just *what* it does.
- **Type hints are the schema.** Use `Literal["a", "b"]` for enums, `int | None = None` for optional, Pydantic models for nested structures. Untyped `*args, **kwargs` won't expose a clean schema.
- **Return type matters.** Tools should return strings or JSON-serializable structures. Returning Python objects (Document, custom classes) often serializes oddly — wrap into a string explicitly.
- **`ToolRuntime`** parameter (LangChain 1.x) lets a tool access the agent's runtime context (config, state). Use sparingly — most tools shouldn't depend on the calling context.
- **Async tools:** decorate `async def` directly with `@tool` — the agent will await them automatically.
- **Tool errors propagate to the LLM** as observation strings. Don't swallow exceptions; let the agent see the failure and decide whether to retry with different args.

## Source

`lesson-6.md` (cells around line 600+ — ReAct agent examples); `lesson-8.md` (cells 14-19 — calendar/email/search tools).
