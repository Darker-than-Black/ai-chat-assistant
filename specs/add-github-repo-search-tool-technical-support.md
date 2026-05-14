# Plan: Add GitHub Repo Search Tool for Technical Support

## Task Description
Add a dedicated GitHub search tool for the `technical_support` worker so public GitHub repositories are searched through a repo-scoped GitHub API tool instead of being smuggled through Tavily's `TECH_SUPPORT_ALLOWED_DOMAINS` whitelist. Keep Tavily for host-level external web search, keep Confluence for internal docs, and make the GitHub tool optional behind a separate repo allowlist in `.env`.

## Objective
When this plan is implemented, `technical_support` will:

- use `TECH_SUPPORT_ALLOWED_DOMAINS` only for real Tavily host filters such as `docs.prozorro.org`, `infobox.prozorro.org`, and `github.com`
- use a new `github_repo_search` LangChain tool for allowlisted repos such as `ProzorroUKR/prozorro-eds`
- continue working when GitHub settings are empty or the GitHub token is absent
- have updated tests, `.env.example`, prompt backup, and architecture docs that reflect the split between Tavily host filtering and repo-level GitHub search

## Problem Statement
The current setup mixes two different concerns into one setting:

- Tavily `include_domains` expects hosts, but current tests/specs still treat GitHub repo URLs or repo-path strings as valid `TECH_SUPPORT_ALLOWED_DOMAINS` inputs.
- Repo-level search inside GitHub documentation, code snippets, and API examples is materially different from public web search and needs a dedicated integration path.
- `.env.example` already advertises `GITHUB_API_TOKEN` and `TECH_SUPPORT_GITHUB_REPOS`, but `config.py` ignores them because those fields do not exist in `Settings`.

This creates an architectural mismatch and weakens Technical Support’s ability to answer questions about public Prozorro libraries such as `prozorro-eds` and `prozorro-pdf`.

## Solution Approach
Split the search surface into three explicit tools for `technical_support`:

1. `confluence_search` for private internal documentation.
2. `github_repo_search` for public documentation/code examples inside a curated set of GitHub repositories.
3. `web_search_technical` for external host-filtered web sources through Tavily.

Implement `github_repo_search` as a thin `httpx`-based wrapper over the GitHub Search API, using `repo:owner/name` qualifiers built from `TECH_SUPPORT_GITHUB_REPOS`. The tool should format results in the same compact text style already used by `web_search.py` and `confluence_search.py`, and it should degrade gracefully to a fallback message on API errors or empty configuration.

At the same time, tighten the Tavily path so `TECH_SUPPORT_ALLOWED_DOMAINS` is treated as a host whitelist, not a pseudo-repo filter. The implementation should preserve backward compatibility for obviously malformed URL-style values by normalizing them to bare hosts, but the documented contract must become host-only.

### Architecture Decisions
- **Affected graph nodes**: only `Technical Support` changes at runtime. `Supervisor`, `Planner`, `Lawyer`, `Common Support`, `Critic`, and `Escalation` routing stay unchanged.
- **Schemas**: no `schemas.py` changes are required. `WorkerResponse` remains the output contract.
- **RAG collection(s)**: neither collection changes. `rag_search_articles` continues to serve `articles` with `TECH_SUPPORT_TAG_WHITELIST`.
- **External calls**: Tavily remains unchanged for host-level web search; a new GitHub REST Search API call is added for repo-scoped search. Rate limits are tighter without `GITHUB_API_TOKEN`, so the tool must support authenticated and unauthenticated requests.
- **Sessions / persistence**: no `PostgresSaver` or session-key changes.
- **Prompt source**: update Langfuse prompt `procurement-technical-support` and mirror the same content in `prompts/procurement-technical-support.md`.

## Relevant Files
Use these files to complete the task:

- [config.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/config.py): add GitHub settings and CSV parsing for `TECH_SUPPORT_GITHUB_REPOS`; optionally normalize host-style Tavily domains in one place.
- [agents/technical_support.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/agents/technical_support.py): bind `github_repo_search` conditionally and keep tool order explicit.
- [tools/web_search.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tools/web_search.py): stop treating repo-path strings as first-class Tavily filters; keep this module focused on host-filtered web search.
- [tools/confluence_search.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tools/confluence_search.py): template for the new `httpx` search tool style and formatted output.
- [prompts/procurement-technical-support.md](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/prompts/procurement-technical-support.md): backup copy of the runtime Technical Support prompt.
- [.env.example](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/.env.example): align comments and examples with the new split between hosts and repos.
- [docs/ARCHITECTURE.md](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/docs/ARCHITECTURE.md): update `§7.1-7.3`, `§11`, and ADR `#12` if the knowledge-source mix or gating changes materially.
- [tests/test_technical_support.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tests/test_technical_support.py): extend tool-wiring tests for optional GitHub binding.
- [tests/test_web_search.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tests/test_web_search.py): remove repo-path assumptions from Tavily-domain tests and keep host-only assertions.
- [tests/evaluations/test_eval_geval.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tests/evaluations/test_eval_geval.py): update the tool-correctness fixture if it still models Technical Support as `web_search` plus `allowed_domains`.

### New Files
- [tools/github_repo_search.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tools/github_repo_search.py): new LangChain `@tool` for allowlisted repo search.
- [tests/test_github_repo_search.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tests/test_github_repo_search.py): focused unit tests for GitHub API request building, allowlist enforcement, formatting, and fallback behavior.
- [tests/test_config.py](/Users/demon/Desktop/mas/MULTI-AGENT-SYSTEMS-HOMEWORKS/course-project/tests/test_config.py): direct tests for CSV parsing and normalization of `tech_support_github_repos` and host-style `tech_support_allowed_domains`.

## Implementation Phases
- [ ] **Phase 1: Config and contract cleanup** - separate Tavily host filtering from GitHub repo allowlisting at the settings level.
  - Status:
  - Comments:

- [ ] **Phase 2: GitHub search tool and Technical Support wiring** - implement the repo search tool and bind it conditionally into `technical_support`.
  - Status:
  - Comments:

- [ ] **Phase 3: Tests, prompt, and docs sync** - cover the new behavior with unit tests and update prompt/docs to match runtime behavior.
  - Status:
  - Comments:

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Config and settings
- [ ] **Add GitHub settings to `Settings`** - define `github_api_token: SecretStr | None = None` and `tech_support_github_repos: Annotated[list[str], NoDecode] = Field(default_factory=list)` in `config.py`.
  - Status:
  - Comments:

- [ ] **Extend CSV parsing for GitHub repos** - update `_split_csv` in `config.py` to parse `tech_support_github_repos` exactly like the existing CSV-backed list fields.
  - Status:
  - Comments:

- [ ] **Normalize the Tavily host contract** - introduce a small helper for `TECH_SUPPORT_ALLOWED_DOMAINS` that converts accidental URL values to bare hosts for backward compatibility, while documenting that host-only values are canonical.
  - Status:
  - Comments:

- [ ] **Define canonical repo value format** - document and enforce `owner/repo` strings for `TECH_SUPPORT_GITHUB_REPOS`; if a full GitHub URL is encountered, normalize it to `owner/repo` rather than treating it as a Tavily domain.
  - Status:
  - Comments:

### 2. GitHub repo search tool
- [ ] **Create `tools/github_repo_search.py` as a LangChain tool** - follow the local `@tool` pattern and add a one-sentence docstring explaining why direct GitHub API search is used instead of Tavily.
  - Status:
  - Comments:

- [ ] **Build a repo-scoped GitHub Search API query** - implement a helper that composes `q=<user query> repo:owner/repo ...` against GitHub’s code-search endpoint so results stay limited to `TECH_SUPPORT_GITHUB_REPOS`.
  - Status:
  - Comments:

- [ ] **Support optional authenticated requests** - add `Authorization` and `Accept` headers when `github_api_token` is set; otherwise use unauthenticated requests and degrade gracefully on rate-limit or permission failures.
  - Status:
  - Comments:

- [ ] **Format GitHub results for LLM consumption** - return compact blocks with `repo`, `path` or file title, snippet, and source URL; keep output size bounded similarly to `web_search.py` and `confluence_search.py`.
  - Status:
  - Comments:

- [ ] **Handle empty config and zero results cleanly** - if `TECH_SUPPORT_GITHUB_REPOS` is empty, the tool should not be bound; if bound but no results are found, return a stable fallback string rather than raising.
  - Status:
  - Comments:

### 3. Technical Support integration
- [ ] **Bind `github_repo_search` conditionally in `technical_support`** - update `build_technical_support_agent()` so the tool list becomes `rag_search_articles`, Tavily web tool, `confluence_search`, and `github_repo_search` only when repos are configured.
  - Status:
  - Comments:

- [ ] **Keep source roles explicit in tool ordering** - preserve a predictable tool order and name surface so prompt guidance can distinguish internal docs, repo docs/code, and external web sources.
  - Status:
  - Comments:

- [ ] **Leave non-technical workers unchanged** - confirm `common_support`, `lawyer`, and graph wiring do not import or bind the new GitHub tool.
  - Status:
  - Comments:

### 4. Tests
- [ ] **Add direct config tests** - create `tests/test_config.py` covering CSV parsing, whitespace trimming, empty-item removal, and normalization for both `tech_support_allowed_domains` and `tech_support_github_repos`.
  - Status:
  - Comments:

- [ ] **Add GitHub tool tests** - create `tests/test_github_repo_search.py` covering request construction, allowlist scoping, result formatting, token header behavior, fallback behavior, and rejection of non-allowlisted repo usage.
  - Status:
  - Comments:

- [ ] **Update Technical Support wiring tests** - extend `tests/test_technical_support.py` to assert that `github_repo_search` is bound only when `tech_support_github_repos` is non-empty and omitted otherwise.
  - Status:
  - Comments:

- [ ] **Update Tavily-domain tests** - adjust `tests/test_web_search.py` so `make_web_search_with_domains()` is asserted against host-only values such as `github.com`, not repo-path strings.
  - Status:
  - Comments:

- [ ] **Update eval/tool-correctness fixtures if needed** - change any fixture that still models Technical Support as generic `web_search` with repo-path `allowed_domains` so it reflects the dedicated GitHub tool.
  - Status:
  - Comments:

### 5. Prompt and documentation
- [ ] **Update the prompt backup file** - revise `prompts/procurement-technical-support.md` so tool guidance explicitly says: `confluence_search` for internal docs, `github_repo_search` for public repo/docs/API material, and `web_search_technical` for external web sources.
  - Status:
  - Comments:

- [ ] **Update the Langfuse runtime prompt manually** - publish the corresponding changes to `procurement-technical-support` in Langfuse, because runtime prompt loading comes from Langfuse rather than local files.
  - Status:
  - Comments:

- [ ] **Update `.env.example` comments and examples** - make `TECH_SUPPORT_ALLOWED_DOMAINS` host-only, set `TECH_SUPPORT_GITHUB_REPOS` examples to `owner/repo`, and note that `GITHUB_API_TOKEN` is optional but recommended for rate limits.
  - Status:
  - Comments:

- [ ] **Update `docs/ARCHITECTURE.md`** - reflect the new source split in `§7.1-7.3`, add GitHub settings to `§11`, and update ADR `#12` or add a new ADR row if the knowledge-source architecture is considered materially changed.
  - Status:
  - Comments:

### 6. Final validation
- [ ] **Run targeted verification and cleanup** - execute focused syntax/import checks and unit tests, then remove any temporary code, stale examples, or drift between docs and runtime behavior.
  - Status:
  - Comments:

## Testing Strategy
Use focused unit tests rather than broad end-to-end coverage for the first implementation.

- `tests/test_config.py` should instantiate `Settings(...)` directly to verify CSV parsing and normalization rules without relying on the global singleton.
- `tests/test_github_repo_search.py` should patch `httpx.get` and assert:
  - search requests contain only `repo:owner/name` qualifiers from the allowlist
  - the query cannot escape into arbitrary repos
  - formatted output includes repo, path/title, snippet, and source URL
  - fallback text is returned for empty results, HTTP errors, and rate-limit responses
- `tests/test_technical_support.py` should verify optional tool binding with and without `tech_support_github_repos`.
- `tests/test_web_search.py` should verify Tavily `include_domains` uses host-only values and no longer treats repo paths as canonical inputs.

## Acceptance Criteria
- `TECH_SUPPORT_ALLOWED_DOMAINS` is documented and tested as a host-only Tavily whitelist.
- GitHub repo URLs are no longer used as pseudo-domain filters for Tavily.
- `config.py` exposes `github_api_token` and `tech_support_github_repos`, and `TECH_SUPPORT_GITHUB_REPOS` is CSV-parsed.
- `tools/github_repo_search.py` exists and searches only inside allowlisted repos.
- `technical_support` binds `github_repo_search` separately from Tavily and only when repos are configured.
- `technical_support` continues to work when GitHub settings are empty.
- Unit tests cover config parsing, GitHub tool behavior, and Technical Support tool wiring.
- `.env.example`, `prompts/procurement-technical-support.md`, Langfuse prompt `procurement-technical-support`, and `docs/ARCHITECTURE.md` are updated consistently.

## Validation Commands
Execute these commands to validate the task is complete:

- `python -m py_compile config.py agents/technical_support.py tools/web_search.py tools/confluence_search.py tools/github_repo_search.py tests/test_config.py tests/test_github_repo_search.py tests/test_technical_support.py tests/test_web_search.py`
- `python -c "import config; import agents.technical_support; import tools.web_search; import tools.confluence_search; import tools.github_repo_search"`
- `pytest tests/test_config.py tests/test_github_repo_search.py tests/test_technical_support.py tests/test_web_search.py -q`

## Notes
- Prefer `httpx` over a new GitHub SDK. The repo already uses `httpx` in `tools/confluence_search.py`, and no extra dependency is needed.
- The missing `scripts/sync_prompts.py` source file means prompt sync should be treated as a manual Langfuse step for this task, even though docs still reference that script.
- Current `.env.example` and `docs/ARCHITECTURE.md §11` are already out of sync on several keys. This task should at least correct the GitHub-related drift; broader env-doc drift can be addressed in the same change if touched nearby.
