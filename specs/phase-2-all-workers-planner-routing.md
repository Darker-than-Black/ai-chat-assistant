# Plan: Phase 2 — All workers + Planner routing

## Task Description

Implement Phase 2 of the Ukrainian public-procurement (Prozorro) support assistant. This vertical slice adds a Planner agent that classifies user queries into one of three domains (legal / procurement_general / technical_system), routes each query to the appropriate worker agent (Lawyer / Common Support / Technical Support), and returns a formatted response. Phase 2 is **single-topic only** (max 1 subtask, no fan-out), no Critic loop, escalation is a stub.

Checklist items covered: **2.1 – 2.7** from `docs/DELIVERY_CHECKLIST.md`.

## Objective

When Phase 2 is complete, `python main.py` accepts any query and:
- Routes legal questions to the existing Lawyer agent
- Routes general procurement questions to a new Common Support agent
- Routes platform/system questions to a new Technical Support agent
- Refuses off-topic queries with a static Ukrainian message
- Stubs escalation for `needs_human=True` plans

**Milestone 2 criterion:** Planner-driven routing works, all 3 workers respond, off-topic is filtered.

## Problem Statement

Phase 1 hardcoded `invoke_lawyer()` in `main.py`. There is no routing logic, no Planner, and two of three worker agents do not exist. The system cannot handle general procurement questions or technical/platform questions. Adding Planner routing requires: a new Tavily web search tool, two new worker agents (Common Support, Technical Support), a Planner agent, a LangGraph StateGraph that wires them together, and bilingual response formatting utilities.

## Solution Approach

Build each component in dependency order (infrastructure → agents → graph → integration → tests), following all three CLAUDE.md development principles:

1. **web_search tool** — Tavily wrapper with hardcoded `language=uk`, `country=UA`, post-filter via `langdetect`, factory for domain-whitelisted variant.
2. **retrieval/retriever.py patch** — extend `_QdrantRetriever` to support list-valued filters (needed for Technical Support's tag whitelist via Qdrant `MatchAny`).
3. **tools/rag.py factory** — `make_rag_search_articles(tag_whitelist)` returns a pre-configured `@tool`; system controls the filter, not the LLM.
4. **Three system prompts** — `prompts/planner.md`, `prompts/common_support.md`, `prompts/technical_support.md`.
5. **Planner agent** — single LLM call via `with_structured_output(ResearchPlan)`, constrained to max 1 subtask via prompt.
6. **Common Support agent** — `create_react_agent` with `rag_search_articles` (no tag filter) + `web_search`.
7. **Technical Support agent** — `create_react_agent` with tag-filtered `rag_search_articles` + domain-restricted `web_search`.
8. **supervisor.py** — `build_graph()` wires 7 nodes + `route_after_planner` conditional edge; compiles with `MemorySaver`.
9. **language.py + final_response.py** — bilingual topic→label map and markdown formatter (ready for Phase 3 multi-section).
10. **main.py** — replaces direct `invoke_lawyer()` with `graph.invoke()`.
11. **Unit tests** — 5 new test files; existing tests remain green.

### Architecture Decisions

- **Affected graph nodes**: new `planner_node`, `common_support_node`, `technical_support_node`, `off_topic_node`, `escalation_stub_node`, `final_response_node`. `lawyer_node` is a thin wrapper over existing `invoke_lawyer()`. No Critic, no fan-out (Phase 3).
- **Schemas**: `GraphState` and all Pydantic contracts already exist in `schemas.py` and are Phase-2-ready. No schema changes needed. `worker_responses: Annotated[list[WorkerResponse], operator.add]` accumulates a single response in Phase 2; this is correct and forward-compatible with Phase 3 fan-out.
- **RAG collections**: `laws` for Lawyer (unchanged), `articles` for Common Support (no tag filter) and Technical Support (tag whitelist from `settings.tech_support_tag_whitelist`).
- **External calls**: Tavily (web_search, language=uk, country=UA). No Slack in Phase 2 (Phase 5). No Langfuse in Phase 2 (Phase 7).
- **Sessions/persistence**: `MemorySaver()` for Phase 2. `PostgresSaver` deferred to Phase 5.
- **Prompt source**: local `prompts/*.md` files. Langfuse Prompt Management deferred to Phase 7.
- **File naming discrepancy**: `DELIVERY_CHECKLIST.md § 2.5` names the graph file `supervisor.py`; `CLAUDE.md` architecture layout names it `agent.py`. Follow the checklist for Phase 2 (`supervisor.py`). Phase 5+ may rename to `agent.py` — add ADR note.
- **`_QdrantRetriever` filter extension**: the current implementation uses `MatchValue` (scalar only). Technical Support needs list-valued tag filter → extend to `MatchAny` for list values. One-line change in `retrieval/retriever.py`.

## Relevant Files

### Existing files to read before implementing

- `schemas.py` — all Pydantic contracts (already complete; no changes needed)
- `config.py` — all settings (already complete; no changes needed)
- `agents/lawyer.py` — pattern to follow for Common Support and Technical Support
- `tools/rag.py` — existing `rag_search` tool; needs `make_rag_search_articles` factory added
- `retrieval/retriever.py` — `_QdrantRetriever` filter handling; needs `MatchAny` for list values
- `prompts/lawyer.md` — prompt format/structure to follow
- `main.py` — current REPL to replace with `graph.invoke()`
- `docs/patterns/pydantic_structured_output.md` — Planner uses `with_structured_output(ResearchPlan)`
- `docs/patterns/langchain_create_agent.md` — worker agents use `create_react_agent(..., response_format=WorkerResponse)`
- `docs/patterns/langgraph_conditional_edges.md` — `route_after_planner` uses mapping dict
- `docs/patterns/langgraph_fanout_with_send.md` — NOT used in Phase 2 (single-topic); read to understand Phase 3 boundary
- `docs/patterns/multiagent_orchestrator_workers.md` — architectural blueprint
- `tests/conftest.py` — existing fixtures to extend
- `tests/test_schemas.py`, `tests/test_retriever.py` — must stay green after Phase 2

### New files to create

- `tools/web_search.py` — Tavily `@tool` + `make_web_search_with_domains()` factory
- `agents/planner.py` — Planner chain: `invoke_planner(query) → ResearchPlan`
- `agents/common_support.py` — Common Support ReAct agent + `invoke_common_support()`
- `agents/technical_support.py` — Technical Support ReAct agent + `invoke_technical_support()`
- `supervisor.py` — LangGraph `build_graph()` + node functions + `route_after_planner()`
- `language.py` — `get_section_label(topic, language)`, `get_no_answer_message(language)`
- `final_response.py` — `format_response(responses, language) → str`
- `prompts/planner.md` — Ukrainian Planner system prompt
- `prompts/common_support.md` — Ukrainian Common Support system prompt
- `prompts/technical_support.md` — Ukrainian Technical Support system prompt
- `tests/test_web_search.py` — unit tests for web_search tool
- `tests/test_planner.py` — unit tests for Planner agent
- `tests/test_common_support.py` — unit tests for Common Support agent
- `tests/test_technical_support.py` — unit tests for Technical Support agent
- `tests/test_graph_routing.py` — integration tests for graph routing

## Implementation Phases

- [ ] **Phase A: Infrastructure (2.1 + retriever patch)** — web_search tool + rag factory + retriever MatchAny fix
  - Status:
  - Comments:

- [ ] **Phase B: Agent implementations (2.2 + 2.3 + 2.4)** — prompts + all three new agents
  - Status:
  - Comments:

- [ ] **Phase C: Graph wiring + utilities (2.5 + 2.7)** — supervisor.py + language.py + final_response.py
  - Status:
  - Comments:

- [ ] **Phase D: Integration + tests (2.6 + testing)** — main.py update + all test files + validation
  - Status:
  - Comments:

## Step by Step Tasks

### 1. retrieval/retriever.py — extend _QdrantRetriever for list-valued filters

- [ ] **Add `MatchAny` import** — add `MatchAny` to the `from qdrant_client.models import ...` line
  - Status:
  - Comments:

- [ ] **Handle list values with MatchAny** — in `_QdrantRetriever._get_relevant_documents`, replace the filter construction loop:
  ```python
  # Before:
  FieldCondition(key=k, match=MatchValue(value=v))
  # After:
  FieldCondition(
      key=k,
      match=MatchAny(any=v) if isinstance(v, list) else MatchValue(value=v)
  )
  ```
  This enables `hybrid_search(query, "articles", filters={"tags": ["tutorial", "procedure"]})`.
  - Status:
  - Comments:

### 2. tools/rag.py — add articles search factory

- [ ] **Add `make_rag_search_articles(tag_whitelist)` factory** — returns a `@tool` named `rag_search_articles` that hardcodes `collection="articles"` and optionally applies a tag filter. The tag_whitelist is passed at agent-build time so the LLM never controls it:
  ```python
  def make_rag_search_articles(tag_whitelist: list[str] | None = None):
      """Returns a tool pre-configured for articles collection.
      tag_whitelist is system-controlled — not exposed to the agent as a parameter.
      """
      @tool
      def rag_search_articles(query: str) -> str:
          """Search Prozorro platform articles for procedural and technical guidance.
          Returns relevant snippets with source citations.
          """
          filters = {"tags": tag_whitelist} if tag_whitelist else None
          chunks = hybrid_search(query, "articles", filters=filters, top_k=settings.rerank_top_k)
          blocks = []
          for chunk in chunks:
              breadcrumb = chunk.metadata.get("breadcrumb") or chunk.metadata.get("title", chunk.doc_id)
              source = chunk.metadata.get("source_url") or chunk.doc_id
              blocks.append(f"---\n{breadcrumb}\n{chunk.text}\nДжерело: {source}")
          context = "\n\n".join(blocks)
          return context[:_MAX_CONTEXT_CHARS] if len(context) > _MAX_CONTEXT_CHARS else context
      return rag_search_articles
  ```
  - Status:
  - Comments:

### 3. tools/web_search.py — Tavily wrapper

- [ ] **Create `tools/web_search.py`** with:
  - Internal `_tavily_search(query, allowed_domains=None)` — calls Tavily with `language="uk"`, `country="UA"`, optional `include_domains`. Returns raw results list. (Note: Tavily ignores `country` without `language` — hence both are always set.)
  - Internal `_is_ukrainian(text: str) -> bool` — `langdetect.detect(text) == "uk"`, catches `LangDetectException` → `False`
  - Internal `_format_results(results, max_snippet=500) -> str` — filters non-Ukrainian, takes first 5, formats as `---\nTitle\nSnippet\nДжерело: url`
  - **`web_search` `@tool`** — calls `_tavily_search(query)`, formats via `_format_results`. Docstring: "Пошук актуальної інформації про публічні закупівлі в Україні. Використовуй для нещодавніх змін або новин. Повертає тільки україномовні результати."
  - **`make_web_search_with_domains(allowed_domains: list[str])` factory** — returns `@tool` named `web_search_technical` that pre-configures `allowed_domains`. Docstring explains it's restricted to approved sources for Prozorro technical support.
  - Status:
  - Comments:

### 4. prompts/planner.md — Planner system prompt

- [ ] **Create `prompts/planner.md`** following the `lawyer.md` format:
  - **Role**: "Ти — класифікатор запитів системи підтримки публічних закупівель ProZorro. Твоє завдання — розуміти запит, визначити до якої категорії він належить, і сформувати структурований план дослідження."
  - **Three categories** with Ukrainian examples per category:
    - `legal` — запити про законодавство (Закон 922-VIII, КМУ 1178, артикули закону, штрафи, порушення)
    - `procurement_general` — запити про процедури (типи тендерів, строки подачі, вимоги до учасників, договори)
    - `technical_system` — запити про платформу (завантаження документів, реєстрація, пошук тендерів, баги, "не працює")
  - **Off-topic detection** (is_on_topic=false): не стосується публічних закупівель в Україні (погода, кулінарія, особисті фінанси, політика, IT поза ProZorro)
  - **Escalation triggers** (needs_human=true): звіти про баги/відсутні функції, незрозумілі ситуації без прецеденту, запити що вимагають правової консультації поза законодавчою базою
  - **Phase 2 constraint**: "Формуй рівно один subtask. Не створюй більше одного підзавдання навіть якщо запит охоплює декілька тем — обери найрелевантніший."
  - **Output format**: the `ResearchPlan` schema with field descriptions
  - Status:
  - Comments:

### 5. agents/planner.py — Planner agent

- [ ] **Create `agents/planner.py`** using `with_structured_output(ResearchPlan)`:
  ```python
  """Planner agent: classifies query and produces a ResearchPlan with at most 1 subtask (Phase 2)."""
  from langchain_core.prompts import ChatPromptTemplate
  from schemas import ResearchPlan
  from agents.lawyer import get_llm
  from pathlib import Path

  _PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

  def invoke_planner(query: str) -> ResearchPlan:
      llm = get_llm()
      chain = (
          ChatPromptTemplate.from_messages([
              ("system", (_PROMPTS_DIR / "planner.md").read_text(encoding="utf-8")),
              ("human", "{query}"),
          ])
          | llm.with_structured_output(ResearchPlan)
      )
      return chain.invoke({"query": query})
  ```
  No singleton caching needed (chain has no mutable state).
  - Status:
  - Comments:

### 6. prompts/common_support.md — Common Support system prompt

- [ ] **Create `prompts/common_support.md`**:
  - **Role**: "Ти — консультант з питань публічних закупівель в Україні. Відповідаєш на загальні процедурні питання: типи закупівель, строки, вимоги до учасників, договори, оскарження."
  - **Normative basis**: Закон 922-VIII, КМУ 1178, 1275, Регламент ProZorro
  - **Procedure**: (1) завжди викликай `rag_search_articles` перш ніж відповідати; (2) якщо відповідь у базі знань неповна — викличи `web_search` для пошуку актуальної інформації; (3) комбінуй результати з обох джерел
  - **Out of scope**: питання про закони та статті (topic=legal) → відповідай found=false з поясненням; технічні питання про платформу (topic=technical_system) → відповідай found=false; неукраїнські закупівлі
  - **Output schema**: `WorkerResponse` з `topic="procurement_general"`, cite джерела
  - Status:
  - Comments:

### 7. agents/common_support.py — Common Support agent

- [ ] **Create `agents/common_support.py`** following `lawyer.py` pattern:
  ```python
  """Common Support agent: general procurement questions via articles RAG + unrestricted web search."""
  from langchain_core.messages import HumanMessage
  from langgraph.prebuilt import create_react_agent
  from agents.lawyer import get_llm
  from schemas import WorkerResponse
  from tools.rag import make_rag_search_articles
  from tools.web_search import web_search
  from pathlib import Path

  _PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
  _common_support = None

  def build_common_support_agent():
      return create_react_agent(
          model=get_llm(),
          tools=[make_rag_search_articles(), web_search],
          prompt=(_PROMPTS_DIR / "common_support.md").read_text(encoding="utf-8"),
          response_format=WorkerResponse,
      )

  def get_common_support_agent():
      global _common_support
      if _common_support is None:
          _common_support = build_common_support_agent()
      return _common_support

  def invoke_common_support(query: str) -> WorkerResponse:
      result = get_common_support_agent().invoke({"messages": [HumanMessage(content=query)]})
      return result["structured_response"]
  ```
  - Status:
  - Comments:

### 8. prompts/technical_support.md — Technical Support system prompt

- [ ] **Create `prompts/technical_support.md`**:
  - **Role**: "Ти — спеціаліст технічної підтримки системи ProZorro. Допомагаєш учасникам і замовникам вирішувати технічні проблеми з платформою."
  - **Bug/feature escalation rule**: "Якщо запит описує помилку системи (баг), відсутню функцію або ситуацію, яку ти не можеш вирішити — встанови `needs_human=true` і поясни причину в `needs_human_reason`. Не вигадуй рішень для системних проблем."
  - **Signals for needs_human=True**: "не відображається", "видає помилку", "не можу авторизуватись", "функція пропала", "хочу щоб система мала"
  - **Procedure**: (1) викликай `rag_search_articles`; (2) якщо недостатньо — виклич `web_search_technical` для пошуку на затверджених сайтах; (3) якщо це баг/відсутня функція → needs_human=true
  - **Out of scope**: юридичні питання (topic=legal), загальні процедури (topic=procurement_general)
  - **Output schema**: `WorkerResponse` з `topic="technical_system"`
  - Status:
  - Comments:

### 9. agents/technical_support.py — Technical Support agent

- [ ] **Create `agents/technical_support.py`** with tag-filtered RAG and domain-whitelisted web search:
  ```python
  """Technical Support agent: platform questions with tag-filtered RAG and domain-restricted web search."""
  from langchain_core.messages import HumanMessage
  from langgraph.prebuilt import create_react_agent
  from agents.lawyer import get_llm
  from schemas import WorkerResponse
  from tools.rag import make_rag_search_articles
  from tools.web_search import make_web_search_with_domains, web_search
  from config import settings
  from pathlib import Path

  _PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
  _technical_support = None

  def build_technical_support_agent():
      tag_whitelist = settings.tech_support_tag_whitelist or None
      allowed_domains = settings.tech_support_allowed_domains
      rag_tool = make_rag_search_articles(tag_whitelist=tag_whitelist)
      web_tool = make_web_search_with_domains(allowed_domains) if allowed_domains else web_search
      return create_react_agent(
          model=get_llm(),
          tools=[rag_tool, web_tool],
          prompt=(_PROMPTS_DIR / "technical_support.md").read_text(encoding="utf-8"),
          response_format=WorkerResponse,
      )

  def get_technical_support_agent():
      global _technical_support
      if _technical_support is None:
          _technical_support = build_technical_support_agent()
      return _technical_support

  def invoke_technical_support(query: str) -> WorkerResponse:
      result = get_technical_support_agent().invoke({"messages": [HumanMessage(content=query)]})
      return result["structured_response"]
  ```
  - Status:
  - Comments:

### 10. agents/lawyer.py — add lawyer_node wrapper

- [ ] **Add `lawyer_node(state: GraphState) -> dict`** to `agents/lawyer.py` — wraps `invoke_lawyer` for use as a LangGraph node:
  ```python
  from schemas import GraphState  # add to imports

  def lawyer_node(state: GraphState) -> dict:
      subtask = state["plan"].subtasks[0]
      return {"worker_responses": [invoke_lawyer(subtask.query)]}
  ```
  Do not break `invoke_lawyer` — `main.py` Phase-1 callers use it until step 14.
  - Status:
  - Comments:

### 11. language.py — bilingual topic→label mapping

- [ ] **Create `language.py`** at repo root:
  ```python
  """Bilingual topic-to-section-label mapping. Extend when new topics are added."""
  _LABELS: dict[str, dict[str, str]] = {
      "legal": {"uk": "Юридична консультація", "en": "Legal Advice"},
      "procurement_general": {"uk": "Загальна інформація про закупівлі", "en": "General Procurement Info"},
      "technical_system": {"uk": "Технічна підтримка", "en": "Technical Support"},
  }
  _NO_ANSWER: dict[str, str] = {
      "uk": "Відповідь не знайдена в базі знань.",
      "en": "No answer found in the knowledge base.",
  }

  def get_section_label(topic: str, language: str = "uk") -> str:
      return _LABELS.get(topic, {}).get(language, topic)

  def get_no_answer_message(language: str = "uk") -> str:
      return _NO_ANSWER.get(language, _NO_ANSWER["uk"])
  ```
  - Status:
  - Comments:

### 12. final_response.py — markdown section formatter

- [ ] **Create `final_response.py`** at repo root. Builds markdown from `list[WorkerResponse]`. Skips sections where `found=False`. Ready for Phase 3 multi-section output:
  ```python
  """Formats worker responses into a user-facing markdown document."""
  from schemas import WorkerResponse
  from language import get_section_label, get_no_answer_message

  def format_response(responses: list[WorkerResponse], language: str = "uk") -> str:
      sections = []
      for resp in responses:
          if not resp.found:
              continue
          label = get_section_label(resp.topic, language)
          sources_md = "\n".join(
              f"- {s.title}" + (f" — {s.url}" if s.url else "")
              for s in resp.sources
          )
          section = f"## {label}\n\n{resp.answer}"
          if sources_md:
              section += f"\n\n**Джерела:**\n{sources_md}"
          sections.append(section)
      return "\n\n---\n\n".join(sections) if sections else get_no_answer_message(language)
  ```
  - Status:
  - Comments:

### 13. supervisor.py — LangGraph Phase-2 graph

- [ ] **Create `supervisor.py`** at repo root with `build_graph()` and module-level `graph = build_graph()`:

  **Node functions** (state-in → state-delta-out):
  ```python
  def planner_node(state: GraphState) -> dict:
      return {"plan": invoke_planner(state["user_message"])}

  def lawyer_node(state: GraphState) -> dict:
      return {"worker_responses": [invoke_lawyer(state["plan"].subtasks[0].query)]}

  def common_support_node(state: GraphState) -> dict:
      return {"worker_responses": [invoke_common_support(state["plan"].subtasks[0].query)]}

  def technical_support_node(state: GraphState) -> dict:
      return {"worker_responses": [invoke_technical_support(state["plan"].subtasks[0].query)]}

  def off_topic_node(state: GraphState) -> dict:
      reason = state["plan"].off_topic_reason or ""
      msg = f"Вибачте, це питання поза межами системи ProZorro.{' ' + reason if reason else ''}"
      return {"final_response": msg, "escalated": False}

  def escalation_stub_node(state: GraphState) -> dict:
      # TODO (Phase 6): replace with EscalationAgent + Slack publish + audit file
      return {"final_response": "Запит передано фахівцю для подальшого опрацювання.", "escalated": True}

  def final_response_node(state: GraphState) -> dict:
      language = (state["plan"].language if state.get("plan") else None) or "uk"
      return {"final_response": format_response(state.get("worker_responses", []), language)}
  ```

  **Router** (pure function, no side effects):
  ```python
  def route_after_planner(state: GraphState) -> str:
      plan = state["plan"]
      if not plan.is_on_topic:
          return "off_topic_node"
      if plan.needs_human:
          return "escalation_stub_node"
      return {
          "legal": "lawyer_node",
          "procurement_general": "common_support_node",
          "technical_system": "technical_support_node",
      }[plan.subtasks[0].topic]
  ```

  **Graph wiring**:
  ```python
  def build_graph():
      builder = StateGraph(GraphState)
      for name, fn in [
          ("planner_node", planner_node), ("lawyer_node", lawyer_node),
          ("common_support_node", common_support_node), ("technical_support_node", technical_support_node),
          ("off_topic_node", off_topic_node), ("escalation_stub_node", escalation_stub_node),
          ("final_response_node", final_response_node),
      ]:
          builder.add_node(name, fn)
      builder.add_edge(START, "planner_node")
      builder.add_conditional_edges(
          "planner_node", route_after_planner,
          {n: n for n in ["lawyer_node", "common_support_node", "technical_support_node",
                           "off_topic_node", "escalation_stub_node"]},
      )
      for worker in ["lawyer_node", "common_support_node", "technical_support_node"]:
          builder.add_edge(worker, "final_response_node")
      builder.add_edge("off_topic_node", END)
      builder.add_edge("escalation_stub_node", END)
      builder.add_edge("final_response_node", END)
      return builder.compile(checkpointer=MemorySaver())

  graph = build_graph()
  ```
  - Status:
  - Comments:

### 14. main.py — replace invoke_lawyer with graph.invoke

- [ ] **Update `main.py`** to use `supervisor.graph`:
  - Remove `from agents.lawyer import invoke_lawyer`
  - Add `from supervisor import graph` and `from uuid import uuid4`
  - Build `initial_state` dict with all `GraphState` fields initialized
  - Call `graph.invoke(initial_state, {"configurable": {"thread_id": session_id}})`
  - Print `result["final_response"]`; if `result.get("escalated")` print escalation notice
  - Keep CLI REPL structure (Ukrainian prompts, exit handling) from Phase 1
  - Keep provider/model header line
  - Status:
  - Comments:

### 15. tests/conftest.py — extend fixtures

- [ ] **Add fixtures** to `tests/conftest.py`:
  - `mock_tavily_results` — list of 3 dicts with `title`, `content` (Ukrainian text), `url` fields
  - `mock_worker_response_common` — `WorkerResponse(topic="procurement_general", found=True, ...)`
  - `mock_worker_response_technical` — `WorkerResponse(topic="technical_system", found=True, ...)`
  - `mock_research_plan_legal` — `ResearchPlan(is_on_topic=True, original_query="...", subtasks=[SubTask(topic="legal", query="...", rationale="...")])`
  - `mock_research_plan_off_topic` — `ResearchPlan(is_on_topic=False, original_query="...", off_topic_reason="...")`
  - `mock_research_plan_escalation` — `ResearchPlan(is_on_topic=True, needs_human=True, escalation_reason="...", original_query="...", subtasks=[SubTask(...)])`
  - Status:
  - Comments:

### 16. tests/test_web_search.py — unit tests for web_search tool

- [ ] **Create `tests/test_web_search.py`** with `unittest.mock.patch("tavily.TavilyClient")`:
  - `test_web_search_returns_ukrainian_only` — mock returns 2 UA + 1 EN result; assert only UA returned
  - `test_web_search_drops_non_ukrainian_by_langdetect` — mock content is English; assert "Результати не знайдено."
  - `test_web_search_with_domains_passes_include_domains` — use `make_web_search_with_domains(["prozorro.gov.ua"])`; assert `TavilyClient.search` called with `include_domains=["prozorro.gov.ua"]`
  - `test_web_search_handles_tavily_exception` — TavilyClient raises; assert returns fallback string
  - `test_web_search_snippet_truncation` — result with content > 500 chars; assert truncated in output
  - Status:
  - Comments:

### 17. tests/test_planner.py — unit tests for Planner agent

- [ ] **Create `tests/test_planner.py`** with mocked LLM (do NOT make real API calls in unit tests):
  - `test_planner_returns_research_plan_instance` — assert `invoke_planner("...")` returns `ResearchPlan`
  - `test_planner_off_topic_detection` — mock returns `ResearchPlan(is_on_topic=False, ...)`; assert `plan.is_on_topic == False` and `plan.subtasks == []`
  - `test_planner_escalation_detection` — mock returns plan with `needs_human=True`; assert `plan.escalation_reason` is not None
  - `test_planner_legal_classification` — mock returns legal subtask; assert `plan.subtasks[0].topic == "legal"`
  - `test_planner_general_classification` — mock returns procurement_general subtask
  - `test_planner_technical_classification` — mock returns technical_system subtask
  - `test_planner_single_subtask_enforced` — assert `len(plan.subtasks) <= 1` for all classification cases

  Use `unittest.mock.patch` on `agents.planner.get_llm` or patch the `with_structured_output` chain.
  - Status:
  - Comments:

### 18. tests/test_common_support.py — unit tests for Common Support agent

- [ ] **Create `tests/test_common_support.py`**:
  - `test_invoke_common_support_returns_worker_response` — mock `get_common_support_agent().invoke`; assert returns `WorkerResponse`
  - `test_common_support_topic_is_procurement_general` — assert `response.topic == "procurement_general"`
  - `test_common_support_not_found_returns_found_false` — mock agent returns `found=False`; assert response propagated correctly
  - Status:
  - Comments:

### 19. tests/test_technical_support.py — unit tests for Technical Support agent

- [ ] **Create `tests/test_technical_support.py`**:
  - `test_invoke_technical_support_returns_worker_response` — mock agent invocation; assert `WorkerResponse`
  - `test_technical_support_topic_is_technical_system` — assert `response.topic == "technical_system"`
  - `test_technical_support_bug_report_sets_needs_human` — mock returns `needs_human=True`; assert propagated
  - `test_technical_support_rag_tool_uses_tag_whitelist` — assert `make_rag_search_articles` called with tag_whitelist from settings (use `settings.tech_support_tag_whitelist`)
  - Status:
  - Comments:

### 20. tests/test_graph_routing.py — integration tests for graph routing

- [ ] **Create `tests/test_graph_routing.py`** using `supervisor.build_graph()` with `MemorySaver`. Patch individual agent invoke functions with mock `WorkerResponse` returns so no real LLM or Qdrant calls are made:
  - `test_legal_query_routes_to_lawyer` — plan with `topic="legal"` → assert `result["worker_responses"][0].topic == "legal"`
  - `test_general_query_routes_to_common_support` — plan with `topic="procurement_general"` → assert correct response topic
  - `test_technical_query_routes_to_technical_support` — plan with `topic="technical_system"` → assert correct response
  - `test_off_topic_query_returns_refusal` — plan with `is_on_topic=False` → assert `"worker_responses"` is empty and `"final_response"` contains refusal text
  - `test_escalation_returns_stub_message` — plan with `needs_human=True` → assert `result["escalated"] == True`
  - `test_final_response_is_not_none_for_all_routes` — parametrize with all valid plan types; assert `result["final_response"]` is not None
  - Status:
  - Comments:

### 21. Validation and cleanup

- [ ] **Run syntax check on all new files**:
  ```bash
  python -m py_compile supervisor.py agents/planner.py agents/common_support.py \
    agents/technical_support.py tools/web_search.py language.py final_response.py
  ```
  - Status:
  - Comments:

- [ ] **Run graph import check**:
  ```bash
  python -c "from supervisor import graph; print(type(graph))"
  ```
  Expected: `<class 'langgraph.graph.state.CompiledStateGraph'>`
  - Status:
  - Comments:

- [ ] **Run full test suite**:
  ```bash
  pytest tests/ -q
  ```
  All tests must be green, including pre-existing `test_schemas.py` and `test_retriever.py`.
  - Status:
  - Comments:

- [ ] **Manual smoke test with `python main.py`**:
  Run four test queries, one per routing path:
  1. `"Яка відповідальність за порушення тендерних процедур відповідно до статті 17 Закону 922?"` → Lawyer (legal)
  2. `"Які документи потрібні для участі у спрощеній закупівлі?"` → Common Support (procurement_general)
  3. `"Не можу завантажити файл в систему, виникає помилка 500"` → Technical Support (technical_system)
  4. `"Яка погода в Києві завтра?"` → off-topic refusal
  - Status:
  - Comments:

- [ ] **Update `docs/DELIVERY_CHECKLIST.md`** — mark 2.1–2.7 as `[x]` after all validation passes. Also mark Phase 4.4 tag pre-filter sub-item `[x]` (implemented in this phase as part of 2.3).
  - Status:
  - Comments:

## Testing Strategy

**Unit tests (mocked LLM and tools):**
- All tests in `tests/test_planner.py`, `tests/test_common_support.py`, `tests/test_technical_support.py` must NOT make real LLM/Qdrant/Tavily calls. Use `unittest.mock.patch` to replace agent invocations.
- Pattern: patch the agent's `invoke` method to return a pre-built `WorkerResponse`; test that the wrapper function correctly extracts `structured_response`.

**Integration tests (`tests/test_graph_routing.py`):**
- Build the real graph but patch `invoke_planner`, `invoke_lawyer`, `invoke_common_support`, `invoke_technical_support` with fixture responses.
- Verifies routing logic and graph wiring without network calls.
- Must cover all 5 routing outcomes: legal, procurement_general, technical_system, off_topic, escalation_stub.

**DeepEval (deferred to Phase 8):**
- Per `DELIVERY_CHECKLIST.md § 8.3`, component-level GEval tests are Phase 8 work.
- Phase 2 only requires pytest unit tests and integration routing tests.

## Acceptance Criteria

1. `python -c "from supervisor import graph; print(type(graph))"` → `<class 'langgraph.graph.state.CompiledStateGraph'>`
2. `python -m py_compile supervisor.py agents/planner.py agents/common_support.py agents/technical_support.py tools/web_search.py language.py final_response.py` → no output (no syntax errors)
3. `pytest tests/ -q` → all tests green, including pre-existing schemas and retriever tests
4. `python main.py` routes a legal query to Lawyer, a general query to Common Support, a technical query to Technical Support, and an off-topic query to the static refusal message — verified manually
5. Technical Support's `rag_search_articles` tool applies `settings.tech_support_tag_whitelist` as a Qdrant `MatchAny` filter (list-valued)
6. `web_search` tool always sends `language="uk"`, `country="UA"` to Tavily; drops non-Ukrainian results via `langdetect`
7. `make_web_search_with_domains(allowed_domains)` restricts Tavily to those domains
8. `format_response([])` and `format_response([WorkerResponse(found=False, ...)])` return the Ukrainian "not found" message (no crash)
9. `docs/DELIVERY_CHECKLIST.md` items 2.1–2.7 all marked `[x]`

## Validation Commands

```bash
# Syntax check all new/modified files
python -m py_compile supervisor.py agents/planner.py agents/common_support.py \
  agents/technical_support.py tools/web_search.py language.py final_response.py \
  retrieval/retriever.py tools/rag.py agents/lawyer.py main.py

# Graph compiles and exports correctly
python -c "from supervisor import graph; print(type(graph))"

# All unit tests pass
pytest tests/ -q

# Manual routing verification (requires docker compose up -d and ingested data)
echo "Яка відповідальність за порушення тендерних процедур?" | python main.py
```

## Notes

**No new packages required** — all dependencies (`tavily-python`, `langdetect`, `langgraph`, `langchain`, `qdrant-client`) are already in `requirements.txt` with pinned versions.

**No new `.env` keys required** — `TAVILY_API_KEY`, `TECH_SUPPORT_ALLOWED_DOMAINS`, `TECH_SUPPORT_TAG_WHITELIST` are already in `config.py` and `.env.example`.

**`GraphState` schema note**: `DELIVERY_CHECKLIST § 2.5` says "без `worker_responses` reducer наразі — single value". The existing `schemas.py` already uses `Annotated[list[WorkerResponse], operator.add]`. Using the existing schema is correct and forward-compatible — Phase 2 just accumulates exactly one item. No schema change needed.

**`supervisor.py` vs `agent.py`**: `DELIVERY_CHECKLIST` uses `supervisor.py`; `CLAUDE.md` architecture layout lists `agent.py`. Follow the checklist for this phase. Add an ADR row in `ARCHITECTURE.md § 15` noting the Phase 2 file is `supervisor.py`; plan to reconcile naming in Phase 5+ when full graph is wired.

**Ingestion prerequisite**: Phase 2 agents require data in Qdrant. Run `docker compose up -d` and `python -m ingest.run_ingest --collection all` before manual smoke testing if Qdrant is empty. This is not a Phase 2 deliverable — data pipeline was done in Phase 1.

**Planner max-subtask enforcement**: enforced via prompt instruction ("формуй рівно один subtask"). Do NOT add a Python-level `model_validator` that truncates subtasks — this would silently discard Planner's reasoning and make multi-subtask Phase 3 harder to enable. The constraint is a Phase 2 *prompt* constraint, not a schema constraint.

**`create_react_agent` import**: use `from langgraph.prebuilt import create_react_agent` (matching `agents/lawyer.py`) — not `langchain.agents.create_agent` from the pattern file. The pattern file covers the LangChain 1.x API; the project pins `langgraph` and uses its prebuilt.