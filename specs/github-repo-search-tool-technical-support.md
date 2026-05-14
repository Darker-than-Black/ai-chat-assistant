# Plan: GitHub Repo Search Tool for Technical Support

> Supersedes `specs/add-github-repo-search-tool-technical-support.md` with concrete
> implementation code derived from full codebase scouting.

## Task Description

Add a dedicated `github_repo_search` LangChain tool for the `technical_support` worker that
searches allowlisted public GitHub repositories via the GitHub REST Search API. Remove the
practice of placing GitHub repository URLs inside `TECH_SUPPORT_ALLOWED_DOMAINS`, which is
semantically a Tavily host whitelist and cannot do repo-scoped searches. Keep Tavily for
external host-filtered web search, Confluence for internal docs, and wire the GitHub tool
conditionally (only when `TECH_SUPPORT_GITHUB_REPOS` is non-empty).

## Objective

After implementation `technical_support`:
- uses `TECH_SUPPORT_ALLOWED_DOMAINS` only for bare Tavily domain hosts (e.g., `docs.prozorro.org`)
- uses `github_repo_search` for repo-scoped search (e.g., `ProzorroUKR/prozorro-eds`)
- continues working when `TECH_SUPPORT_GITHUB_REPOS` is empty or GitHub token is absent
- has updated config, tests, `.env.example`, prompt backup, and `docs/ARCHITECTURE.md`

## Problem Statement

`TECH_SUPPORT_ALLOWED_DOMAINS` was designed as a domain whitelist for Tavily's `include_domains`
parameter. Tavily expects bare hosts, not full URLs or path segments. Current `.env.example`
advertises `GITHUB_API_TOKEN` and `TECH_SUPPORT_GITHUB_REPOS`, but `config.py` has no
corresponding `Settings` fields — those env vars are silently ignored at runtime. Even after
URL-scheme stripping (already present in `tools/web_search.py:80`), passing GitHub repo paths
like `github.com/ProzorroUKR/prozorro-eds` to Tavily results in host-only matching
(`github.com`), not repo-scoped matching. Tavily is also inappropriate for searching code
snippets, method signatures, and README files inside a specific repository.

## Solution Approach

Split the technical support search surface into four explicit sources:

1. `confluence_search` — private Confluence internal documentation (existing, env-gated)
2. `rag_search_articles` — curated Qdrant knowledge-base articles (existing, tag-filtered)
3. `github_repo_search` — public GitHub repository files/docs/code (new, repo-list-gated)
4. `web_search_technical` — external web via Tavily with host whitelist (existing)

Implement `github_repo_search` as a thin `httpx`-based wrapper over
`GET https://api.github.com/search/code` using `repo:owner/name` qualifiers built from
`TECH_SUPPORT_GITHUB_REPOS`. Use the `text-match` media type to get inline snippets.
Degrade gracefully on API errors, rate-limit responses, and empty repo configuration.

### Architecture Decisions

- **Affected graph nodes**: only `technical_support` worker changes. Supervisor, Planner,
  Lawyer, Common Support, Critic, Escalation are untouched.
- **Schemas**: no changes to `schemas.py`. `WorkerResponse` remains the output contract.
- **RAG collections**: unchanged. `rag_search_articles` keeps `articles` collection with tag filter.
- **External calls**: GitHub REST Search API (`api.github.com/search/code`). Rate limits:
  10 req/min unauthenticated, 30 req/min with token. Tool must handle 403/429 gracefully.
- **Sessions / persistence**: no `PostgresSaver` or session-key changes.
- **Prompt source**: update `prompts/procurement-technical-support.md` (backup) AND publish the
  same change manually to Langfuse prompt `procurement-technical-support`.

## Relevant Files

- `config.py` — add `github_api_token` and `tech_support_github_repos`; extend `_split_csv` validator
- `agents/technical_support.py` — conditionally bind `github_repo_search` in `build_technical_support_agent()`
- `tools/web_search.py` — no logic changes needed (URL-scheme stripping already exists); update comment
- `prompts/procurement-technical-support.md` — add `github_repo_search` tool section
- `.env.example` — clarify host-only format for `TECH_SUPPORT_ALLOWED_DOMAINS`; set `TECH_SUPPORT_GITHUB_REPOS` to `owner/repo` format
- `docs/ARCHITECTURE.md` — update § 7.3 (Technical Support tools), § 11 (config table), § 15 ADR
- `tests/test_technical_support.py` — extend tool-wiring tests for GitHub conditional binding
- `tests/test_web_search.py` — ensure domain tests use host-only values (not repo paths)
- `tests/evaluations/test_eval_geval.py` — update tool-correctness fixtures at lines 347, 365, 383

### New Files

- `tools/github_repo_search.py` — new LangChain `@tool` factory with `httpx` GitHub Search API integration
- `tests/test_github_repo_search.py` — unit tests: request construction, allowlist scoping, formatting, fallback
- `tests/test_config.py` — direct Settings instantiation tests for CSV parsing and normalization

## Implementation Phases

- [ ] **Phase 1: Config and contract cleanup** - add GitHub fields to `Settings`; document `TECH_SUPPORT_ALLOWED_DOMAINS` as host-only
  - Status:
  - Comments:

- [ ] **Phase 2: GitHub search tool and Technical Support wiring** - implement `tools/github_repo_search.py`; update `build_technical_support_agent()`
  - Status:
  - Comments:

- [ ] **Phase 3: Tests, prompt, and docs sync** - unit tests; update prompt; update architecture docs
  - Status:
  - Comments:

## Step by Step Tasks

### 1. Config (`config.py`)

- [ ] **Add two new fields to `Settings`** — insert after `tech_support_tag_whitelist` (around line 37):
  ```python
  github_api_token: SecretStr | None = None
  tech_support_github_repos: Annotated[list[str], NoDecode] = Field(default_factory=list)
  ```
  - Status:
  - Comments:

- [ ] **Extend `_split_csv` validator** — add `"tech_support_github_repos"` to the `@field_validator(...)` field list. The existing validator trims whitespace and removes empty items — that is the correct behavior for repo slugs too. Example: `"ProzorroUKR/prozorro-eds, ProzorroUKR/prozorro-pdf"` → `["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"]`.
  - Status:
  - Comments:

- [ ] **Verify `TECH_SUPPORT_ALLOWED_DOMAINS` contract is already safe** — `tools/web_search.py:80` already strips `https://` scheme with `d.split("://", 1)[1] if "://" in d else d`. No config-level change needed. Add an inline comment in `config.py` to the `tech_support_allowed_domains` field clarifying its expected format: `# Tavily host whitelist; bare domains only (e.g. docs.prozorro.org)`.
  - Status:
  - Comments:

### 2. New Tool (`tools/github_repo_search.py`)

- [ ] **Create the file with module docstring and imports** — the docstring must explain *why* direct GitHub API is used instead of Tavily (one sentence per CLAUDE.md convention):
  ```python
  """
  GitHub REST Code Search wrapper — used because Tavily's include_domains cannot
  scope searches to a specific repository path; only GitHub's native search API
  supports repo: qualifiers.
  """

  import httpx
  from langchain_core.tools import tool

  from config import settings
  ```
  - Status:
  - Comments:

- [ ] **Add constants and helpers** — keep output bounded consistently with other tools:
  ```python
  _FALLBACK = "Документацію у репозиторіях GitHub не знайдено або сталася помилка запиту."
  _SEARCH_URL = "https://api.github.com/search/code"
  _MAX_RESULTS = 5
  _MAX_SNIPPET_CHARS = 400
  _MAX_TOTAL_CHARS = 8_000


  def _to_repo_slug(value: str) -> str:
      """Extract owner/repo from a full GitHub URL or pass a bare slug through."""
      if "github.com/" in value:
          return value.split("github.com/", 1)[1].strip("/")
      return value.strip("/")


  def _build_headers() -> dict[str, str]:
      headers: dict[str, str] = {
          "Accept": "application/vnd.github.text-match+json",
          "X-GitHub-Api-Version": "2022-11-28",
      }
      if settings.github_api_token:
          headers["Authorization"] = (
              f"Bearer {settings.github_api_token.get_secret_value()}"
          )
      return headers
  ```
  - Status:
  - Comments:

- [ ] **Implement `_search_repos` and `_format_results` helpers**:
  ```python
  def _search_repos(query: str, slugs: list[str]) -> list[dict]:
      repo_qualifiers = " ".join(f"repo:{slug}" for slug in slugs)
      resp = httpx.get(
          _SEARCH_URL,
          params={"q": f"{query} {repo_qualifiers}", "per_page": _MAX_RESULTS},
          headers=_build_headers(),
          timeout=10.0,
      )
      resp.raise_for_status()
      return resp.json().get("items", [])


  def _format_results(items: list[dict]) -> str:
      blocks: list[str] = []
      total = 0
      for item in items:
          repo = item.get("repository", {}).get("full_name", "?")
          path = item.get("path", "?")
          html_url = item.get("html_url", "")
          matches = item.get("text_matches", [])
          snippet = matches[0].get("fragment", "")[:_MAX_SNIPPET_CHARS] if matches else ""
          block = f"**{path}** ({repo})\n{snippet}\nДжерело: {html_url}"
          if total + len(block) > _MAX_TOTAL_CHARS:
              break
          blocks.append(block)
          total += len(block)
      return "\n\n---\n\n".join(blocks) if blocks else _FALLBACK
  ```
  - Status:
  - Comments:

- [ ] **Implement `make_github_repo_search` factory** — mirrors the pattern of `make_web_search_with_domains` and `make_rag_search_articles`:
  ```python
  def make_github_repo_search(repos: list[str]):
      slugs = [_to_repo_slug(r) for r in repos]

      @tool("github_repo_search")
      def github_repo_search(query: str) -> str:
          """Пошук документації, коду та API-специфікацій у дозволених GitHub-репозиторіях Prozorro."""
          try:
              items = _search_repos(query, slugs)
              return _format_results(items)
          except Exception:
              return _FALLBACK

      return github_repo_search
  ```
  - Status:
  - Comments:

### 3. Agent Update (`agents/technical_support.py`)

- [ ] **Add import for the new tool** — add to imports at the top:
  ```python
  from tools.github_repo_search import make_github_repo_search
  ```
  - Status:
  - Comments:

- [ ] **Update `build_technical_support_agent()`** — conditionally append the GitHub tool:

  **Before (lines 21–35):**
  ```python
  def build_technical_support_agent():  # type: ignore[return]
      tag_whitelist = settings.tech_support_tag_whitelist or None
      allowed_domains = settings.tech_support_allowed_domains
      rag_tool = make_rag_search_articles(tag_whitelist=tag_whitelist)
      web_tool = (
          make_web_search_with_domains(allowed_domains)
          if allowed_domains
          else web_search
      )
      return create_react_agent(
          model=get_llm(),
          tools=[rag_tool, web_tool, confluence_search],
          prompt=_load_system_prompt(),
          response_format=WorkerResponse,
      )
  ```

  **After:**
  ```python
  def build_technical_support_agent():  # type: ignore[return]
      tag_whitelist = settings.tech_support_tag_whitelist or None
      allowed_domains = settings.tech_support_allowed_domains
      github_repos = settings.tech_support_github_repos
      rag_tool = make_rag_search_articles(tag_whitelist=tag_whitelist)
      web_tool = (
          make_web_search_with_domains(allowed_domains)
          if allowed_domains
          else web_search
      )
      tools = [rag_tool, confluence_search, web_tool]
      if github_repos:
          tools.append(make_github_repo_search(github_repos))
      return create_react_agent(
          model=get_llm(),
          tools=tools,
          prompt=_load_system_prompt(),
          response_format=WorkerResponse,
      )
  ```

  Tool order in list: `rag_search_articles`, `confluence_search`, `web_search_technical`, then
  `github_repo_search` appended last. The prompt governs invocation order; list order is for
  display/discovery only.
  - Status:
  - Comments:

### 4. Prompt Backup (`prompts/procurement-technical-support.md`)

- [ ] **Add `github_repo_search` to "Порядок роботи з інструментами"** — change the numbered list to:
  ```
  1. `confluence_search` — спочатку шукай у внутрішній документації Confluence.
  2. `rag_search_articles` — шукай у базі знань статей Prozorro.
  3. `github_repo_search` — шукай документацію, код та API-специфікації у публічних репозиторіях GitHub (якщо інструмент доступний).
  4. `web_search_technical` — шукай у затверджених зовнішніх джерелах.
  ```
  - Status:
  - Comments:

- [ ] **Add `github_repo_search` to "Доступні інструменти" section** — add a new `###` block after the `confluence_search` block:
  ```markdown
  ### `github_repo_search`
  Пошук у публічних GitHub-репозиторіях Prozorro: документація, README, API-специфікації, code snippets.
  Використовуй для питань про npm-бібліотеки (`@prozorro/prozorro-eds`, `@prozorro/prozorro-pdf`):
  методи, параметри, приклади використання.
  Інструмент доступний лише коли `TECH_SUPPORT_GITHUB_REPOS` налаштовано.
  ```
  - Status:
  - Comments:

- [ ] **Update `web_search_technical` description** — remove mention of `TECH_SUPPORT_ALLOWED_DOMAINS` from the prompt and replace with plain description:
  ```markdown
  ### `web_search_technical`
  Пошук у затверджених зовнішніх технічних джерелах (обмежено доменним whitelist).
  Використовуй після `confluence_search`, `rag_search_articles` і `github_repo_search`.
  ```
  - Status:
  - Comments:

- [ ] **Publish updated prompt to Langfuse manually** — open Langfuse UI → Prompt Management → `procurement-technical-support` → edit → apply the same changes → save as new version and promote to `production` label. This is a manual step; `scripts/sync_prompts.py` is referenced in docs but does not exist.
  - Status:
  - Comments:

### 5. `.env.example`

- [ ] **Update GitHub section** — the file already has `GITHUB_API_TOKEN` and `TECH_SUPPORT_GITHUB_REPOS` (lines 12–13). Change the values from full URLs to `owner/repo` slugs and add format clarification comment:
  ```
  # ── GitHub repo search ────────────────────────────────────────────
  GITHUB_API_TOKEN=ghp_***                              # optional; raises rate limit from 10 to 30 req/min
  TECH_SUPPORT_GITHUB_REPOS=ProzorroUKR/prozorro-eds,ProzorroUKR/prozorro-pdf   # owner/repo slugs (CSV)
  ```
  - Status:
  - Comments:

- [ ] **Update `TECH_SUPPORT_ALLOWED_DOMAINS` comment** — clarify it is a host-only whitelist with no paths:
  ```
  TECH_SUPPORT_ALLOWED_DOMAINS=docs.prozorro.org,infobox.prozorro.org,github.com   # bare hosts only — no https://, no /path
  ```
  - Status:
  - Comments:

### 6. `docs/ARCHITECTURE.md`

- [ ] **Update § 7.3 Technical Support tools** — change the tools table/list to show four sources:
  | Tool | Data source | Gating condition |
  |------|------------|-----------------|
  | `confluence_search` | Confluence Cloud | `CONFLUENCE_URL` + `CONFLUENCE_API_TOKEN` set |
  | `rag_search_articles` | Qdrant `articles` collection | always available |
  | `github_repo_search` | GitHub REST Search API | `TECH_SUPPORT_GITHUB_REPOS` non-empty |
  | `web_search_technical` | Tavily (host whitelist) | always available (falls back to generic `web_search` if no domains) |
  - Status:
  - Comments:

- [ ] **Update § 11 Configuration** — add two rows to the config table:
  - `GITHUB_API_TOKEN` → `github_api_token: SecretStr | None` — GitHub Personal Access Token (optional, read:public_repo scope)
  - `TECH_SUPPORT_GITHUB_REPOS` → `tech_support_github_repos: list[str]` — CSV of `owner/repo` slugs for repo-scoped search
  - Also add inline note that `TECH_SUPPORT_ALLOWED_DOMAINS` accepts bare hosts only (no scheme, no path)
  - Status:
  - Comments:

- [ ] **Add ADR row in § 15** — new entry:
  > **ADR #13 — GitHub repo search via REST API instead of Tavily**
  > GitHub repository documentation, code snippets, and API specs require repo-scoped search that Tavily's `include_domains` cannot provide. Implemented as a thin `httpx` wrapper over `api.github.com/search/code` using `repo:owner/name` qualifiers. Chose not to ingest GitHub into Qdrant (Phase 1.3) to keep the tool simple and always up-to-date without a re-ingest cycle. Trade-off: rate-limited (30 req/min with token); mitigated by optional `GITHUB_API_TOKEN` and graceful fallback.
  - Status:
  - Comments:

### 7. Tests

- [ ] **Create `tests/test_config.py`** — test CSV parsing for new fields using direct `Settings(...)` instantiation:
  ```python
  from config import Settings

  def test_github_repos_csv_parsed():
      s = Settings(TECH_SUPPORT_GITHUB_REPOS="ProzorroUKR/prozorro-eds, ProzorroUKR/prozorro-pdf")
      assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"]

  def test_github_repos_empty_by_default():
      s = Settings()
      assert s.tech_support_github_repos == []

  def test_github_repos_empty_string():
      s = Settings(TECH_SUPPORT_GITHUB_REPOS="")
      assert s.tech_support_github_repos == []

  def test_allowed_domains_host_only():
      s = Settings(TECH_SUPPORT_ALLOWED_DOMAINS="docs.prozorro.org,infobox.prozorro.org")
      assert s.tech_support_allowed_domains == ["docs.prozorro.org", "infobox.prozorro.org"]

  def test_github_api_token_is_secret():
      s = Settings(GITHUB_API_TOKEN="ghp_test123")
      assert s.github_api_token is not None
      assert s.github_api_token.get_secret_value() == "ghp_test123"
  ```
  - Status:
  - Comments:

- [ ] **Create `tests/test_github_repo_search.py`** — mock `httpx.get`, assert API request construction and output formatting:
  ```python
  import json
  import pytest
  import httpx
  from unittest.mock import MagicMock, patch
  from tools.github_repo_search import (
      make_github_repo_search,
      _to_repo_slug,
      _FALLBACK,
  )
  from config import settings

  # --- Slug normalization ---

  def test_slug_from_full_url():
      assert _to_repo_slug("https://github.com/ProzorroUKR/prozorro-eds") == "ProzorroUKR/prozorro-eds"

  def test_slug_passthrough():
      assert _to_repo_slug("ProzorroUKR/prozorro-eds") == "ProzorroUKR/prozorro-eds"

  def test_slug_strips_trailing_slash():
      assert _to_repo_slug("https://github.com/ProzorroUKR/prozorro-eds/") == "ProzorroUKR/prozorro-eds"

  # --- Request construction ---

  def _mock_response(items: list[dict]) -> MagicMock:
      mock = MagicMock()
      mock.json.return_value = {"items": items, "total_count": len(items)}
      mock.raise_for_status.return_value = None
      return mock

  def test_search_scoped_to_allowlisted_repos(monkeypatch):
      captured = {}
      def fake_get(url, *, params, headers, timeout):
          captured["params"] = params
          captured["headers"] = headers
          return _mock_response([])
      monkeypatch.setattr(httpx, "get", fake_get)
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      tool.invoke({"query": "sign document"})
      assert "repo:ProzorroUKR/prozorro-eds" in captured["params"]["q"]
      assert "sign document" in captured["params"]["q"]

  def test_multiple_repos_in_single_query(monkeypatch):
      captured = {}
      def fake_get(url, *, params, headers, timeout):
          captured["params"] = params
          return _mock_response([])
      monkeypatch.setattr(httpx, "get", fake_get)
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"])
      tool.invoke({"query": "init"})
      q = captured["params"]["q"]
      assert "repo:ProzorroUKR/prozorro-eds" in q
      assert "repo:ProzorroUKR/prozorro-pdf" in q

  def test_token_added_to_auth_header_when_set(monkeypatch):
      captured = {}
      def fake_get(url, *, params, headers, timeout):
          captured["headers"] = headers
          return _mock_response([])
      monkeypatch.setattr(httpx, "get", fake_get)
      monkeypatch.setattr(settings, "github_api_token", __import__("pydantic", fromlist=["SecretStr"]).SecretStr("ghp_test"))
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      tool.invoke({"query": "test"})
      assert "Authorization" in captured["headers"]
      assert "ghp_test" in captured["headers"]["Authorization"]

  def test_no_auth_header_without_token(monkeypatch):
      captured = {}
      def fake_get(url, *, params, headers, timeout):
          captured["headers"] = headers
          return _mock_response([])
      monkeypatch.setattr(httpx, "get", fake_get)
      monkeypatch.setattr(settings, "github_api_token", None)
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      tool.invoke({"query": "test"})
      assert "Authorization" not in captured["headers"]

  # --- Formatting ---

  def test_formats_repo_path_snippet_url(monkeypatch):
      item = {
          "path": "README.md",
          "html_url": "https://github.com/ProzorroUKR/prozorro-eds/blob/main/README.md",
          "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
          "text_matches": [{"fragment": "ProzorroEds.init() initializes the library"}],
      }
      monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response([item]))
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      result = tool.invoke({"query": "init"})
      assert "README.md" in result
      assert "ProzorroUKR/prozorro-eds" in result
      assert "ProzorroEds.init()" in result
      assert "https://github.com" in result

  # --- Fallback behavior ---

  def test_fallback_on_empty_results(monkeypatch):
      monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response([]))
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      assert tool.invoke({"query": "xyz"}) == _FALLBACK

  def test_fallback_on_http_error(monkeypatch):
      def raise_error(*a, **kw):
          raise httpx.HTTPStatusError("rate limited", request=MagicMock(), response=MagicMock())
      monkeypatch.setattr(httpx, "get", raise_error)
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      assert tool.invoke({"query": "test"}) == _FALLBACK

  def test_fallback_on_network_error(monkeypatch):
      monkeypatch.setattr(httpx, "get", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("timeout")))
      tool = make_github_repo_search(["ProzorroUKR/prozorro-eds"])
      assert tool.invoke({"query": "test"}) == _FALLBACK
  ```
  - Status:
  - Comments:

- [ ] **Extend `tests/test_technical_support.py`** — add two tests for conditional tool binding. Use the same monkeypatching pattern already present in the file:
  ```python
  def test_github_tool_bound_when_repos_configured(monkeypatch):
      monkeypatch.setattr(settings, "tech_support_github_repos", ["ProzorroUKR/prozorro-eds"])
      agent = build_technical_support_agent()
      tool_names = {t.name for t in agent.tools}
      assert "github_repo_search" in tool_names

  def test_github_tool_absent_when_repos_empty(monkeypatch):
      monkeypatch.setattr(settings, "tech_support_github_repos", [])
      agent = build_technical_support_agent()
      tool_names = {t.name for t in agent.tools}
      assert "github_repo_search" not in tool_names
  ```
  - Status:
  - Comments:

- [ ] **Update `tests/test_web_search.py`** — verify that `make_web_search_with_domains` tests use host-only values (e.g., `"github.com"`, `"docs.prozorro.org"`), not repo-path strings. Remove any assertion that treats `github.com/ProzorroUKR/prozorro-eds` as a valid `allowed_domains` entry for Tavily.
  - Status:
  - Comments:

- [ ] **Check `tests/evaluations/test_eval_geval.py` fixtures at lines 347, 365, 383** — if the fixture for Technical Support tool correctness still lists `allowed_domains` with GitHub repo URLs or expects only three tools (`rag`, `web_search`, `confluence`), update the expected tool set to include conditional `github_repo_search`. Verify whether the fixture needs to specify repo list presence.
  - Status:
  - Comments:

### 8. Final Validation

- [ ] **Run syntax check on all changed files**:
  ```bash
  python -m py_compile config.py agents/technical_support.py tools/github_repo_search.py tests/test_config.py tests/test_github_repo_search.py tests/test_technical_support.py
  ```
  - Status:
  - Comments:

- [ ] **Run import check**:
  ```bash
  python -c "from config import settings; from agents.technical_support import build_technical_support_agent; from tools.github_repo_search import make_github_repo_search; print('OK')"
  ```
  - Status:
  - Comments:

- [ ] **Run targeted unit tests**:
  ```bash
  pytest tests/test_config.py tests/test_github_repo_search.py tests/test_technical_support.py tests/test_web_search.py -q
  ```
  - Status:
  - Comments:

- [ ] **Run full test suite** to catch regressions:
  ```bash
  pytest tests/ -m "not eval" -q
  ```
  - Status:
  - Comments:

## Testing Strategy

Focus on unit tests with `httpx.get` patching — no real GitHub API calls in CI.

- `tests/test_config.py`: instantiate `Settings(...)` directly to avoid global singleton side-effects. Cover CSV parsing, empty values, whitespace trimming, and SecretStr handling.
- `tests/test_github_repo_search.py`: patch `httpx.get` via `monkeypatch`. Cover:
  - slug normalization from full URLs and bare slugs
  - `repo:` qualifier injected into query string
  - multiple repos combined into single query
  - Authorization header present/absent based on token config
  - text_matches fragment extracted into snippet
  - fallback on empty results, HTTP error, network error
- `tests/test_technical_support.py`: patch `settings.tech_support_github_repos` and call `build_technical_support_agent()` to assert tool presence/absence.
- `tests/test_web_search.py`: ensure existing host-filter tests use only valid bare-host values.
- `tests/evaluations/test_eval_geval.py`: update any stale fixture that mis-describes Technical Support tool set.

## Acceptance Criteria

1. `config.py` exposes `github_api_token: SecretStr | None` and `tech_support_github_repos: list[str]`, and the CSV validator parses `TECH_SUPPORT_GITHUB_REPOS`.
2. GitHub URLs no longer appear as pseudo-domain filters in Tavily (`TECH_SUPPORT_ALLOWED_DOMAINS` is host-only in docs and `.env.example`).
3. `tools/github_repo_search.py` exists; `make_github_repo_search(repos)` returns a `@tool("github_repo_search")` function that queries only allowlisted repos.
4. `technical_support` binds `github_repo_search` only when `TECH_SUPPORT_GITHUB_REPOS` is non-empty.
5. `technical_support` works correctly when `TECH_SUPPORT_GITHUB_REPOS` is empty (no tool, no error).
6. `tests/test_config.py` and `tests/test_github_repo_search.py` exist and pass.
7. `tests/test_technical_support.py` includes conditional-binding tests and they pass.
8. `prompts/procurement-technical-support.md` lists all four tools with their roles.
9. `docs/ARCHITECTURE.md` reflects the four-tool architecture in § 7.3, § 11, and § 15.
10. `.env.example` documents `TECH_SUPPORT_ALLOWED_DOMAINS` as host-only and `TECH_SUPPORT_GITHUB_REPOS` as `owner/repo` format.

## Validation Commands

```bash
# Syntax check all touched files
python -m py_compile config.py agents/technical_support.py tools/github_repo_search.py \
  tests/test_config.py tests/test_github_repo_search.py tests/test_technical_support.py \
  tests/test_web_search.py

# Import smoke test
python -c "
from config import settings
from agents.technical_support import build_technical_support_agent
from tools.github_repo_search import make_github_repo_search
print('imports OK')
"

# Targeted unit tests (no LLM, no external APIs)
pytest tests/test_config.py tests/test_github_repo_search.py \
  tests/test_technical_support.py tests/test_web_search.py -q

# Full non-eval suite (regression guard)
pytest tests/ -m "not eval" -q
```

## Notes

- **Library choice**: use `httpx` (already in `requirements.txt >= 0.27`). No new dependency needed.
  Do NOT add `PyGithub` or `github3.py` — they add weight without benefit for this use case.
- **Rate limits**: GitHub code search is 10 req/min unauthenticated, 30 req/min with token.
  A typical agent session calls each tool 1–3 times per query, so a token is strongly
  recommended for production use. Graceful fallback is mandatory for the tokenless path.
- **Multi-repo query**: GitHub code search supports multiple `repo:` qualifiers in a single `q`
  string (OR semantics). Batch all allowed repos into one request instead of N requests.
- **`text_matches` header**: the `Accept: application/vnd.github.text-match+json` header is
  required to get snippet fragments in the response. Without it, `text_matches` is absent.
- **Prompt sync**: `scripts/sync_prompts.py` is referenced in `docs/ARCHITECTURE.md` but does
  not exist in the repo. Langfuse prompt update must be done manually through the UI.
- **Prior spec**: `specs/add-github-repo-search-tool-technical-support.md` is a prior planning
  document that covers the same feature at a higher level. This spec supersedes it with
  concrete implementation code.
