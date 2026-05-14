# Plan: Add Confluence Cloud Search Tool to Technical Support Agent

## Current Status

**Phase 1 (Foundation)** — COMPLETE (committed in `0a5b581 small fixes`):
- `config.py`: 4 Confluence fields added, `_split_csv` validator extended
- `requirements.txt`: `httpx>=0.27` added
- `.env.example`: Confluence section added

**Phase 2 (Core Tool)** — PENDING

**Phase 3 (Integration)** — PENDING

---

## Task Description

Add a new `confluence_search` LangChain tool that queries a private Confluence Cloud instance via its REST API (CQL search). The tool is conditionally bound to the Technical Support agent — it appears in the agent's tool list only when `CONFLUENCE_URL` and `CONFLUENCE_API_TOKEN` are configured. This gives the agent access to private internal documentation alongside its existing RAG and restricted Tavily web search.

## Objective

When this plan is complete, a technical query routed to Technical Support will trigger a real Confluence CQL search when Confluence credentials are configured, and the agent will cite internal Confluence pages alongside its other sources. When credentials are absent the agent behaves exactly as before (no regression).

## Problem Statement

The Technical Support agent currently searches only the infobox RAG collection (`articles`) and the Tavily-filtered web. Private internal documentation (API integration guides, onboarding how-tos, internal troubleshooting runbooks) lives in Confluence and is inaccessible to the agent. Users asking about internal configuration or private processes cannot be helped by the current tool set.

## Solution Approach

Add a thin `@tool`-decorated wrapper (`tools/confluence_search.py`) that calls the Confluence Cloud content-search endpoint via `httpx`, applies CQL filtering, strips HTML from page excerpts with stdlib `re`, and formats output following the `"---\nTitle\nExcerpt\nДжерело: URL"` convention already used by `tools/rag.py` and `tools/web_search.py`. The tool is appended to the `tools` list in `build_technical_support_agent()` only when `settings.confluence_url` and `settings.confluence_api_token` are both set.

### Architecture Decisions

- **Affected graph nodes**: Technical Support only. Planner, Lawyer, Common Support, Critic, Escalation are untouched.
- **Schemas**: No changes to `schemas.py`. `WorkerResponse.sources` already holds `list[Source]` — Confluence URLs flow through normally.
- **RAG collection(s)**: Neither `laws` nor `articles`. Confluence is a separate live external source; no ingestion into Qdrant is needed or desired (live search preserves freshness).
- **External calls**: `httpx.get` to `{CONFLUENCE_URL}/rest/api/content/search` with Basic Auth (email + API token). Timeout 10 s. Max 5 results per query. CQL filters by page type and optionally by space keys.
- **Sessions / persistence**: No change to `PostgresSaver` checkpoint format.
- **Prompt source**: Langfuse prompt `procurement-technical-support` must be updated to mention `confluence_search` and when to use it. A local backup is created at `prompts/technical_support.md`. The Langfuse update is a manual step (no Langfuse Management API call in code).

## Relevant Files

- `config.py` — ✅ DONE: 4 new fields added, `_split_csv` validator covers `confluence_space_keys`
- `.env.example` — ✅ DONE: Confluence section added
- `requirements.txt` — ✅ DONE: `httpx>=0.27` added
- `agents/technical_support.py` — add top-level import + conditional tool append inside `build_technical_support_agent()`
- `agents/lawyer.py` — read-only reference for `get_llm()` import pattern
- `tools/web_search.py` — reference for `@tool`, fallback string, `try/except` error handling pattern
- `tools/rag.py` — reference for `_format_*` helper and `_MAX_CONTEXT_CHARS` truncation
- `tests/test_web_search.py` — reference for `patch("tools.module.httpx.get")` + `monkeypatch.setattr(module.settings, ...)` pattern
- `tests/test_technical_support.py` — add 2 new conditional-binding tests; existing test at line 121 passes as-is when `confluence_url=None`
- `docs/ARCHITECTURE.md` — add Confluence to Technical Support § 2.3 + ADR entry in § 15
- `observability/langfuse_client.py` — read-only reference for `load_prompt` call

### New Files
- `tools/confluence_search.py` — new `@tool` wrapping Confluence REST API
- `tests/test_confluence_search.py` — 7 unit tests with mocked `httpx.get`
- `prompts/technical_support.md` — local backup of Langfuse prompt with new tool

## Implementation Phases

- [x] **Phase 1: Foundation** — Config + deps. No behavioural change.
  - Status: COMPLETE (committed in `0a5b581 small fixes`)
  - Comments: config.py, requirements.txt, .env.example all updated

- [ ] **Phase 2: Core Tool** — Implement `tools/confluence_search.py` with full error handling and tests.
  - Status: PENDING
  - Comments:

- [ ] **Phase 3: Integration** — Wire tool into agent, update prompt backup, update architecture doc, run full test suite.
  - Status: PENDING
  - Comments:

## Step by Step Tasks

### 1. Dependencies (ALREADY DONE)

- [x] **`httpx>=0.27` in `requirements.txt`** — added with comment `# HTTP client (Confluence search; transitive dep of langchain-openai)`.
  - Status: DONE
  - Comments: Committed in 0a5b581

- [x] **Confluence fields in `config.py`** — `confluence_url`, `confluence_username`, `confluence_api_token`, `confluence_space_keys` added after `# ── Slack ──` block.
  - Status: DONE
  - Comments: Committed in 0a5b581

- [x] **`_split_csv` extended** — `"confluence_space_keys"` added to the `@field_validator` decorator.
  - Status: DONE
  - Comments: Committed in 0a5b581

- [x] **`.env.example` updated** — Confluence section added after Slack block.
  - Status: DONE
  - Comments: Committed in 0a5b581

### 2. Tool Implementation

- [ ] **Create `tools/confluence_search.py`** — implement the full module:

  ```python
  """Confluence Cloud search tool for private technical documentation.

  Bound to Technical Support only when CONFLUENCE_URL and CONFLUENCE_API_TOKEN
  are configured. Searches pages via CQL; optionally restricts to CONFLUENCE_SPACE_KEYS.
  """

  from __future__ import annotations

  import re

  import httpx
  from langchain_core.tools import tool

  from config import settings

  _FALLBACK = "Документацію в Confluence не знайдено."
  _MAX_EXCERPT_CHARS = 500
  _MAX_RESULTS = 5
  _MAX_CONTEXT_CHARS = 6000


  def _strip_html(html: str) -> str:
      return re.sub(r"<[^>]+>", " ", html).strip()


  def _search_confluence(query: str) -> list[dict]:
      assert settings.confluence_url, "CONFLUENCE_URL required"
      assert settings.confluence_username, "CONFLUENCE_USERNAME required"
      assert settings.confluence_api_token, "CONFLUENCE_API_TOKEN required"

      cql = f'text~"{query}" AND type=page'
      if settings.confluence_space_keys:
          keys = ",".join(settings.confluence_space_keys)
          cql += f" AND space.key IN ({keys})"

      resp = httpx.get(
          f"{settings.confluence_url}/rest/api/content/search",
          params={
              "cql": cql,
              "limit": _MAX_RESULTS,
              "expand": "body.view",
          },
          auth=(
              settings.confluence_username,
              settings.confluence_api_token.get_secret_value(),
          ),
          timeout=10.0,
      )
      resp.raise_for_status()
      return resp.json().get("results", [])


  def _format_results(results: list[dict], base_url: str) -> str:
      blocks = []
      for page in results:
          title = page.get("title", "")
          webui = page.get("_links", {}).get("webui", "")
          url = f"{base_url}{webui}" if webui else base_url
          raw_html = page.get("body", {}).get("view", {}).get("value", "")
          text = _strip_html(raw_html)
          excerpt = text[:_MAX_EXCERPT_CHARS]
          if len(text) > _MAX_EXCERPT_CHARS:
              excerpt = f"{excerpt}..."
          blocks.append(f"---\n{title}\n{excerpt}\nДжерело: {url}")
          if len(blocks) == _MAX_RESULTS:
              break
      context = "\n\n".join(blocks)
      return context[:_MAX_CONTEXT_CHARS] if len(context) > _MAX_CONTEXT_CHARS else context


  @tool
  def confluence_search(query: str) -> str:
      """Search the internal Confluence knowledge base for Prozorro technical documentation.

      Use this tool FIRST for questions about internal processes, API integration guides,
      configuration how-tos, and troubleshooting documented in the company Confluence.
      Prefer this over web_search_technical for private internal documentation that
      would not appear in public web search.
      Returns Confluence page excerpts with source URLs.
      """
      try:
          results = _search_confluence(query)
          if not results:
              return _FALLBACK
          return _format_results(results, settings.confluence_url)  # type: ignore[arg-type]
      except Exception:
          return _FALLBACK
  ```
  - Status:
  - Comments:

- [ ] **Create `tests/test_confluence_search.py`** — 7 unit tests following `tests/test_web_search.py` pattern (monkeypatch on `confluence_module.settings`, `patch("tools.confluence_search.httpx.get")`):

  ```python
  from types import SimpleNamespace
  from unittest.mock import patch

  import pytest

  import tools.confluence_search as confluence_module
  from tools.confluence_search import (
      _FALLBACK,
      _strip_html,
      confluence_search,
  )


  @pytest.fixture
  def confluence_settings_stub(monkeypatch: pytest.MonkeyPatch) -> None:
      monkeypatch.setattr(confluence_module.settings, "confluence_url", "https://acme.atlassian.net/wiki")
      monkeypatch.setattr(confluence_module.settings, "confluence_username", "user@acme.com")
      monkeypatch.setattr(
          confluence_module.settings,
          "confluence_api_token",
          SimpleNamespace(get_secret_value=lambda: "test-token"),
      )
      monkeypatch.setattr(confluence_module.settings, "confluence_space_keys", [])


  def _page(title: str, webui: str, html: str) -> dict:
      return {"title": title, "_links": {"webui": webui}, "body": {"view": {"value": html}}}


  def test_confluence_search_returns_formatted_results(confluence_settings_stub: None) -> None:
      pages = [_page("API Guide", "/pages/1", "<p>Інструкція з інтеграції</p>")]
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.json.return_value = {"results": pages}
          mock_get.return_value.raise_for_status.return_value = None
          result = confluence_search.invoke({"query": "API інтеграція"})
      assert "API Guide" in result
      assert "Інструкція з інтеграції" in result
      assert "https://acme.atlassian.net/wiki/pages/1" in result


  def test_confluence_search_strips_html_tags(confluence_settings_stub: None) -> None:
      pages = [_page("Guide", "/pages/2", "<h1>Заголовок</h1><p>Текст</p>")]
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.json.return_value = {"results": pages}
          mock_get.return_value.raise_for_status.return_value = None
          result = confluence_search.invoke({"query": "guide"})
      assert "<h1>" not in result
      assert "<p>" not in result
      assert "Заголовок" in result
      assert "Текст" in result


  def test_confluence_search_returns_fallback_on_no_results(confluence_settings_stub: None) -> None:
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.json.return_value = {"results": []}
          mock_get.return_value.raise_for_status.return_value = None
          result = confluence_search.invoke({"query": "something missing"})
      assert result == _FALLBACK


  def test_confluence_search_returns_fallback_on_http_error(confluence_settings_stub: None) -> None:
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.raise_for_status.side_effect = Exception("403 Forbidden")
          result = confluence_search.invoke({"query": "query"})
      assert result == _FALLBACK


  def test_confluence_search_applies_space_key_filter(
      confluence_settings_stub: None,
      monkeypatch: pytest.MonkeyPatch,
  ) -> None:
      monkeypatch.setattr(confluence_module.settings, "confluence_space_keys", ["TECH", "PROC"])
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.json.return_value = {"results": []}
          mock_get.return_value.raise_for_status.return_value = None
          confluence_search.invoke({"query": "test"})
      cql = mock_get.call_args.kwargs["params"]["cql"]
      assert "space.key IN (TECH,PROC)" in cql


  def test_confluence_search_no_space_filter_when_empty(confluence_settings_stub: None) -> None:
      with patch("tools.confluence_search.httpx.get") as mock_get:
          mock_get.return_value.json.return_value = {"results": []}
          mock_get.return_value.raise_for_status.return_value = None
          confluence_search.invoke({"query": "test"})
      cql = mock_get.call_args.kwargs["params"]["cql"]
      assert "space.key" not in cql


  def test_strip_html_removes_all_tags() -> None:
      assert "Title" in _strip_html("<h1>Title</h1><p>Body</p>")
      assert "Body" in _strip_html("<h1>Title</h1><p>Body</p>")
      assert "<" not in _strip_html("<h1>Title</h1><p>Body</p>")
      assert _strip_html("No tags") == "No tags"
      assert _strip_html("") == ""
  ```
  - Status:
  - Comments:

### 3. Agent Integration

- [ ] **Update `agents/technical_support.py`** — add top-level import and conditional tool binding.

  Add import at the top of the file (after existing imports):
  ```python
  from tools.confluence_search import confluence_search
  ```

  Replace the `return create_react_agent(...)` call inside `build_technical_support_agent()`:
  ```python
  # Before (current code):
  return create_react_agent(
      model=get_llm(),
      tools=[rag_tool, web_tool],
      prompt=_load_system_prompt(),
      response_format=WorkerResponse,
  )

  # After:
  tools = [rag_tool, web_tool]
  if settings.confluence_url and settings.confluence_api_token:
      tools.append(confluence_search)
  return create_react_agent(
      model=get_llm(),
      tools=tools,
      prompt=_load_system_prompt(),
      response_format=WorkerResponse,
  )
  ```

  **Note on existing tests**: The test `test_technical_support_rag_tool_uses_tag_whitelist` (line 121 in `test_technical_support.py`) asserts `tools=[rag_tool, web_tool]`. Since `settings.confluence_url` defaults to `None`, the conditional is `False` and the tools list remains 2 items — this test passes WITHOUT changes.
  - Status:
  - Comments:

- [ ] **Update `tests/test_technical_support.py`** — add 2 new tests for the conditional Confluence binding. Append after the last existing test:

  ```python
  def test_technical_support_includes_confluence_when_configured(monkeypatch) -> None:
      rag_tool = object()
      web_tool = object()
      llm = object()
      created_agent = SimpleNamespace(name="technical-support-agent")
      make_rag_search_articles = Mock(return_value=rag_tool)
      make_web_search_with_domains = Mock(return_value=web_tool)
      create_react_agent = Mock(return_value=created_agent)

      monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
      monkeypatch.setattr("agents.technical_support.make_web_search_with_domains", make_web_search_with_domains)
      monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
      monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
      monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
      monkeypatch.setattr(settings, "tech_support_allowed_domains", ["prozorro.gov.ua"])
      monkeypatch.setattr(settings, "confluence_url", "https://acme.atlassian.net/wiki")
      monkeypatch.setattr(
          settings,
          "confluence_api_token",
          SimpleNamespace(get_secret_value=lambda: "tok"),
      )

      build_technical_support_agent()

      tools_arg = create_react_agent.call_args.kwargs["tools"]
      assert len(tools_arg) == 3
      assert tools_arg[2].name == "confluence_search"


  def test_technical_support_excludes_confluence_when_not_configured(monkeypatch) -> None:
      rag_tool = object()
      llm = object()
      created_agent = SimpleNamespace(name="technical-support-agent")
      make_rag_search_articles = Mock(return_value=rag_tool)
      create_react_agent = Mock(return_value=created_agent)

      monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
      monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
      monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
      monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
      monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
      monkeypatch.setattr(settings, "confluence_url", None)
      monkeypatch.setattr(settings, "confluence_api_token", None)

      build_technical_support_agent()

      tools_arg = create_react_agent.call_args.kwargs["tools"]
      assert len(tools_arg) == 2
      assert all(getattr(t, "name", None) != "confluence_search" for t in tools_arg)
  ```

  Also add `SimpleNamespace` to existing import at line 1 — it's already there (`from types import SimpleNamespace`). No import changes needed.
  - Status:
  - Comments:

### 4. Prompt Backup

- [ ] **Create `prompts/` directory and `prompts/technical_support.md`**:

  ```markdown
  # Technical Support Agent

  ## Role
  You are the Technical Support Agent for the Prozorro electronic procurement system.
  You help users with technical issues: Prozorro API integration, PDF generation,
  platform errors, and internal configuration.

  ## Tool Usage Order
  1. `confluence_search` — search internal Confluence documentation FIRST (if available).
  2. `rag_search_articles` — search the curated articles knowledge base.
  3. `web_search_technical` — search approved external documentation sources.

  ## Instructions
  - Search at least two sources before composing your answer.
  - Cite every source in the `sources` field of your response.
  - If you find detailed documentation in Confluence, prefer it over web results.
  - If no relevant information is found in any source, set `found=False` and
    `needs_human=True` with a clear `needs_human_reason`.

  ## Available Tools
  - `confluence_search`: Search the internal Confluence knowledge base for technical
    guides, API specs, and internal process documentation. Use BEFORE web_search_technical.
  - `rag_search_articles`: Search the curated Prozorro articles knowledge base.
  - `web_search_technical`: Search approved external technical documentation sources.

  ## Response Format
  Return a `WorkerResponse`:
  - `topic`: always `"technical_system"`
  - `found`: `true` if relevant information was found
  - `answer`: detailed technical explanation (markdown)
  - `sources`: list of Source objects (`{url, title}`) from all sources used
  - `confidence`: 0.0–1.0
  - `needs_human`: `true` only if this is a bug report or feature request
  - `needs_human_reason`: reason for escalation if `needs_human` is `true`
  ```
  - Status:
  - Comments:

- [ ] **Update Langfuse prompt `procurement-technical-support`** — **MANUAL STEP**. Log in to Langfuse dashboard, open `procurement-technical-support`, add `confluence_search` tool description and updated "Tool Usage Order" matching `prompts/technical_support.md`. Publish with label `production`.
  - Status:
  - Comments:

### 5. Architecture Documentation

- [ ] **Update `docs/ARCHITECTURE.md` § 2.3 (Technical Support)** — add Confluence as third tool source. Find the "Technical Support" agent section and extend the tools list:
  ```
  **Tools:**
  - `confluence_search(query)` — Confluence Cloud CQL search, optional, bound only when
    `CONFLUENCE_URL` + `CONFLUENCE_API_TOKEN` are set; restricted to `CONFLUENCE_SPACE_KEYS`
    if configured
  - `rag_search_articles(query)` — hybrid RAG search over `articles` collection, pre-filtered
    by `tags` matching `TECH_SUPPORT_TAG_WHITELIST`
  - `web_search_technical(query)` — Tavily search restricted to `TECH_SUPPORT_ALLOWED_DOMAINS`
  ```
  - Status:
  - Comments:

- [ ] **Add ADR entry to `docs/ARCHITECTURE.md` § 15** — find the highest existing ADR number and increment by 1:
  ```
  | ADR-N | Confluence Cloud as third knowledge source for Technical Support |
  | Date  | 2026-05-05 |
  | Decision | Add optional live Confluence search tool to Technical Support agent.
               Rationale: internal process documentation lives in Confluence and is not
               public-web-searchable. Tool is conditionally bound (env-gated) so the
               agent remains functional with or without Confluence credentials. |
  | Alternatives considered | Ingest Confluence pages into the `articles` Qdrant collection.
                               Rejected: stale data risk (Confluence updates don't trigger
                               re-ingestion), duplicate storage cost, freshness maintenance burden. |
  ```
  - Status:
  - Comments:

### 6. Validation

- [ ] **Run syntax check**:
  ```bash
  python -m py_compile tools/confluence_search.py agents/technical_support.py config.py
  ```
  - Status:
  - Comments:

- [ ] **Run Confluence tool tests**:
  ```bash
  pytest tests/test_confluence_search.py -v
  ```
  All 7 tests must pass.
  - Status:
  - Comments:

- [ ] **Run Technical Support tests**:
  ```bash
  pytest tests/test_technical_support.py -v
  ```
  All existing tests + 2 new ones must pass (7 total).
  - Status:
  - Comments:

- [ ] **Run full test suite**:
  ```bash
  pytest tests/ -q --ignore=tests/evaluations
  ```
  Must exit 0 with 0 failures.
  - Status:
  - Comments:

- [ ] **Graph import sanity check**:
  ```bash
  python -c "from supervisor import build_graph; print('graph ok')"
  ```
  - Status:
  - Comments:

## Testing Strategy

**Unit tests** (`tests/test_confluence_search.py`): 7 tests covering happy path, empty results, HTTP 4xx errors, CQL space-key filter present and absent, HTML stripping (inline), and `_strip_html` helper directly. All HTTP calls mocked via `patch("tools.confluence_search.httpx.get")`. Settings monkeypatched on `confluence_module.settings` following the `test_web_search.py` pattern.

**Agent wiring tests** (`tests/test_technical_support.py`): 2 new tests verify the tool list is `[rag_tool, web_tool, confluence_search]` when credentials are configured and `[rag_tool, web_tool]` when they are absent. Existing tests are unaffected — the conditional is `False` when `settings.confluence_url=None` (the default), so the assertions at line 121 (`tools=[rag_tool, web_tool]`) continue to hold.

**No LLM evaluation tests** at this stage — the tool is an HTTP wrapper; its quality depends on Confluence content, which is user-managed.

## Acceptance Criteria

1. `pytest tests/test_confluence_search.py -v` passes all 7 tests.
2. `pytest tests/test_technical_support.py -v` passes all tests including the 2 new conditional-binding tests (7 total).
3. `pytest tests/ -q --ignore=tests/evaluations` exits 0 with 0 failures.
4. `python -m py_compile tools/confluence_search.py agents/technical_support.py config.py` exits 0.
5. When `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN` are set in `.env`, `build_technical_support_agent()` returns an agent with 3 tools.
6. When Confluence env vars are absent, agent has 2 tools (no regression).
7. `docs/ARCHITECTURE.md` mentions `confluence_search` in the Technical Support section and has an ADR entry.
8. `prompts/technical_support.md` exists and mentions all 3 tools.
9. Langfuse prompt `procurement-technical-support` is updated (manual verification).

## Validation Commands

```bash
# Syntax check
python -m py_compile tools/confluence_search.py agents/technical_support.py config.py

# Confluence tool unit tests
pytest tests/test_confluence_search.py -v

# Technical Support agent tests
pytest tests/test_technical_support.py -v

# Full suite
pytest tests/ -q --ignore=tests/evaluations

# Graph sanity
python -c "from supervisor import build_graph; print('graph ok')"
```

## Notes

- **`httpx` is a transitive dep** of `langchain-openai` (via `openai>=1.x`) and is already installed. Adding it to `requirements.txt` makes the dependency explicit, matching project convention.
- **HTML stripping via `re.sub`** is intentionally simple — Confluence body content uses standard HTML tags (`<p>`, `<h1>`, `<ul>`, `<li>`); regex tag removal is sufficient for excerpt generation. If richer parsing is needed later, `beautifulsoup4` can be added.
- **Top-level import** of `confluence_search` in `agents/technical_support.py` is safe because `httpx` is always installed. The conditional inside `build_technical_support_agent()` controls whether the LLM sees the tool — the module always imports cleanly.
- **Singleton cache**: `_technical_support` is built once per process. Confluence credentials must be present at agent startup to activate the tool; runtime credential changes are not reflected until process restart.
- **The Langfuse update is a manual step** — the codebase has no Langfuse Management API client.
- **Confluence space keys format**: CQL `IN (KEY1,KEY2)` expects unquoted keys. Standard Confluence space keys (uppercase alphanumeric) require no quoting.
- **Rate limits**: Confluence Cloud REST API typically allows 300–600 req/min. With `max_results=5` and tool calls triggered only on user queries, staying within limits is not a concern at this scale.
- **`docs/ARCHITECTURE.md` § 15 ADR numbering**: read the file to find the highest existing ADR number and increment by 1.
