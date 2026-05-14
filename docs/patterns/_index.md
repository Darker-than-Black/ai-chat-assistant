# References index

Lecture-derived patterns, one file per concept. Use as the **first** source for framework APIs — these are pinned to the versions taught in the course.

## When to read

Before invoking a framework feature you haven't used in this repo yet. Fast discovery: `ls docs/patterns/` then read the relevant file (or this index).

## Catalog

### Pydantic — contracts between agents
- **`pydantic_structured_output.md`** — `with_structured_output(SchemaModel)` for typed LLM responses.
- **`pydantic_validators.md`** — `@model_validator(mode="after")` for cross-field invariants.

### LangGraph — graph, state, control flow
- **`langgraph_state_typeddict.md`** — `TypedDict` + `Annotated[..., reducer]` for shared state.
- **`langgraph_conditional_edges.md`** — routing functions, mapping dicts, `Command` API.
- **`langgraph_fanout_with_send.md`** — dynamic parallel dispatch via `Send` (key pattern for our fan-out).
- **`langgraph_postgres_checkpointer.md`** — `PostgresSaver` for persistent sessions.

### LangChain agents
- **`langchain_create_agent.md`** — `create_agent` (1.x API) for ReAct-style workers.
- **`langchain_tool_decorator.md`** — `@tool` decorator, docstrings as descriptions, type hints as schemas.
- **`langchain_hitl_middleware.md`** — `HumanInTheLoopMiddleware` for tool-call gating (reference; not currently used).

### RAG
- **`rag_chunking_and_embeddings.md`** — `RecursiveCharacterTextSplitter`, OpenAI embeddings.
- **`rag_hybrid_ensemble.md`** — `EnsembleRetriever` with BM25 + vector.
- **`rag_cross_encoder_reranking.md`** — `CrossEncoderReranker` via `ContextualCompressionRetriever`.

### External services
- **`tavily_search.md`** — `TavilySearchResults` wrapper, language/domain filtering.
- **`slack_bolt_basics.md`** — Slack Bolt event handling, posting, Socket Mode.

### Observability and testing
- **`langfuse_integration.md`** — `CallbackHandler`, `propagate_attributes`, prompt management.
- **`deepeval_geval_pattern.md`** — `GEval` with `evaluation_steps`, `ToolCorrectnessMetric`.

### Architecture references
- **`multiagent_orchestrator_workers.md`** — Anthropic's pattern that this project implements.
- **`protocols_mcp_acp_overview.md`** — MCP / ACP overview (NOT used here; reference only).

## Source notebooks

If a needed pattern isn't covered, consult the original lecture notebooks in `docs/lectures/`:

| Lesson | Topic |
|---|---|
| 5 | RAG: chunking, embeddings, hybrid search, reranking |
| 6 | LangGraph fundamentals: StateGraph, MessagesState, ReAct |
| 7 | Multi-agent patterns (Anthropic): Routing, Orchestrator-Workers, Evaluator-Optimizer, Send API |
| 8 | Production multi-agent: `create_agent` 1.x, HITL middleware, Tavily, RAG agents |
| 9 | MCP + ACP protocols (not used here) |
| 10 | DeepEval: GEval, ToolCorrectness, Faithfulness, AnswerRelevancy |
| 11 | Production deployment: checkpointing, durable execution (partial use) |
| 12 | Langfuse: tracing, prompt management, LLM-as-a-Judge |

When extracting a new pattern, follow the format of existing files: *when to use → minimal example → pitfalls → source*.
