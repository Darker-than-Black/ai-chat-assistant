# Plan: Fix TECH_SUPPORT_ALLOWED_DOMAINS — URL scheme stripping

## Task Description

The Technical Support agent always escalates on technical queries instead of searching the approved documentation sources. The root cause is that `TECH_SUPPORT_ALLOWED_DOMAINS` in `.env` contains full URLs with `https://` scheme prefix (e.g. `https://prozorro-api-docs.readthedocs.io/en/master`), but Tavily's `include_domains` parameter expects bare domain strings (e.g. `prozorro-api-docs.readthedocs.io/en/master`). Tavily silently returns zero results when passed scheme-prefixed values, so the agent finds nothing and escalates.

## Objective

After this fix, a technical query routed to Technical Support will trigger a real Tavily web search restricted to the configured documentation domains, and the agent will return a populated `WorkerResponse` instead of escalating due to empty search results.

## Problem Statement

**Call chain that fails:**

```
.env → TECH_SUPPORT_ALLOWED_DOMAINS=https://prozorro-api-docs.readthedocs.io/en/master,...
  ↓ config._split_csv validator
settings.tech_support_allowed_domains = ["https://prozorro-api-docs.readthedocs.io/en/master", ...]
  ↓ agents/technical_support.py:22
allowed_domains = settings.tech_support_allowed_domains   # still full URLs
  ↓ tools/web_search.py:76
locked_domains = list(allowed_domains)                    # still full URLs
  ↓ tools/web_search.py:29
include_domains=allowed_domains or None                   # Tavily rejects https:// prefix
  ↓ Tavily API
results = []                                              # zero matches
  ↓ _format_results([])
return "Результати не знайдено."                          # fallback string
  ↓ agent has no web data + sparse RAG → found=False, low confidence
  ↓ Critic scores below threshold
→ ESCALATION
```

**Evidence from docs:**  
`docs/patterns/tavily_search.md` — pitfalls section: "`include_domains` is a hard filter. If the whitelist excludes too many domains, you'll get zero results". The pattern example shows bare domain strings, not full URLs.

## Solution Approach

Apply URL scheme stripping inside `make_web_search_with_domains()` in `tools/web_search.py`. This is the defensive layer — regardless of what format the operator uses in `.env`, the call to Tavily always receives bare domain strings. Simultaneously correct `.env` and `.env.example` to document the canonical format.

No schema changes, no graph rewiring, no re-ingestion needed.

### Architecture Decisions

- **Affected graph nodes**: none — fix is entirely inside `tools/web_search.py` (utility layer)
- **Schemas**: no changes to Pydantic models
- **RAG collection(s)**: not involved
- **External calls**: Tavily — the `include_domains` kwarg must contain strings without `://`
- **Sessions / persistence**: no change
- **Prompt source**: no change — the agent prompt already says to use `web_search` for technical docs

## Relevant Files

- `tools/web_search.py` — **primary fix**: add scheme-stripping in `make_web_search_with_domains()` (line 75-90)
- `.env` — **config fix**: replace full URLs with scheme-stripped equivalents
- `.env.example` — **doc fix**: add note explaining the required format with an example value
- `tests/test_web_search.py` — **test fix**: add test case that passes full URLs to `make_web_search_with_domains` and asserts they are stripped before reaching Tavily

## Step by Step Tasks

### 1. Fix `tools/web_search.py`

- [ ] **Strip URL scheme in `make_web_search_with_domains`** — on line 76, replace `locked_domains = list(allowed_domains)` with a one-liner that strips `https://` / `http://` from each entry:
  ```python
  locked_domains = [d.split("://", 1)[1] if "://" in d else d for d in allowed_domains]
  ```
  This is the only code change required in production code. The `_tavily_search` function receives a clean list and no other callers need changes.
  - Status:
  - Comments:

### 2. Fix `.env`

- [ ] **Replace full URLs with scheme-stripped values** — update the line:
  ```
  # Before
  TECH_SUPPORT_ALLOWED_DOMAINS=https://prozorro-api-docs.readthedocs.io/en/master,https://github.com/ProzorroUKR/prozorro-pdf

  # After
  TECH_SUPPORT_ALLOWED_DOMAINS=prozorro-api-docs.readthedocs.io/en/master,github.com/ProzorroUKR/prozorro-pdf
  ```
  The trailing path (`/en/master`, `/ProzorroUKR/prozorro-pdf`) is preserved — Tavily supports domain+path restriction and this limits results to the relevant section.
  - Status:
  - Comments:

### 3. Fix `.env.example`

- [ ] **Add format documentation** — update the comment above `TECH_SUPPORT_ALLOWED_DOMAINS` to clarify the expected format and add an example value so future operators don't repeat the same mistake:
  ```
  # CSV — bare domain names, no https:// prefix (Tavily rejects scheme-prefixed values).
  # Example: prozorro-api-docs.readthedocs.io/en/master,github.com/ProzorroUKR/prozorro-pdf
  TECH_SUPPORT_ALLOWED_DOMAINS=
  ```
  - Status:
  - Comments:

### 4. Add test for URL normalization

- [ ] **Add `test_web_search_with_domains_strips_url_scheme`** to `tests/test_web_search.py` — pass full URLs with `https://` to `make_web_search_with_domains` and assert that Tavily receives the stripped versions:
  ```python
  def test_web_search_with_domains_strips_url_scheme(tavily_api_key_stub: None) -> None:
      restricted_search = make_web_search_with_domains(
          [
              "https://prozorro-api-docs.readthedocs.io/en/master",
              "https://github.com/ProzorroUKR/prozorro-pdf",
          ]
      )
      with patch("tools.web_search.TavilyClient") as mock_tavily_client:
          mock_tavily_client.return_value.search.return_value = {"results": []}
          restricted_search.invoke({"query": "помилка API"})
      assert mock_tavily_client.return_value.search.call_args.kwargs["include_domains"] == [
          "prozorro-api-docs.readthedocs.io/en/master",
          "github.com/ProzorroUKR/prozorro-pdf",
      ]
  ```
  This test would have caught the original bug before it reached production. Place it directly after the existing `test_web_search_with_domains_passes_include_domains` test.
  - Status:
  - Comments:

### 5. Validate

- [ ] **Run syntax check** — ensure no import errors were introduced:
  ```bash
  python -m py_compile tools/web_search.py agents/technical_support.py config.py
  ```
  - Status:
  - Comments:

- [ ] **Run web search test suite** — all existing tests must still pass plus the new one:
  ```bash
  pytest tests/test_web_search.py -v
  ```
  - Status:
  - Comments:

- [ ] **Run full test suite** — verify no regressions:
  ```bash
  pytest tests/ -q --ignore=tests/evaluations
  ```
  - Status:
  - Comments:

- [ ] **Manual smoke test** — start the graph and send a technical query (requires real API keys). Confirm that:
  - The agent calls `web_search_technical` (visible in Langfuse traces or stdout logs)
  - The `WorkerResponse.sources` list contains URLs from `prozorro-api-docs.readthedocs.io` or `github.com/ProzorroUKR`
  - No escalation occurs for a clearly answerable technical question (e.g. "Як отримати токен доступу до Prozorro API?")
  - Status:
  - Comments:

## Testing Strategy

Unit tests in `tests/test_web_search.py` cover the fix at the unit level via `mock_tavily_client`. The new test (`test_web_search_with_domains_strips_url_scheme`) directly verifies the normalization logic. Existing tests remain unchanged and confirm that bare domain strings still pass through correctly (no double-stripping).

## Acceptance Criteria

1. `pytest tests/test_web_search.py -v` passes including the new `test_web_search_with_domains_strips_url_scheme` test.
2. `pytest tests/ -q --ignore=tests/evaluations` exits 0 with no regressions.
3. A technical query routed to Technical Support produces a `WorkerResponse` with `found=True` and at least one entry in `sources` from the configured domains — confirmed via Langfuse trace or log output.
4. The `.env` no longer contains `https://` in `TECH_SUPPORT_ALLOWED_DOMAINS`.
5. The `.env.example` comment explains the bare-domain-name requirement with a concrete example.

## Validation Commands

```bash
# Syntax check
python -m py_compile tools/web_search.py agents/technical_support.py config.py

# Unit tests — web search module
pytest tests/test_web_search.py -v

# Full suite (fast, no LLM calls)
pytest tests/ -q --ignore=tests/evaluations

# Graph import sanity
python -c "from supervisor import build_graph; print('graph ok')"
```

## Notes

- No library changes, no `requirements.txt` updates needed.
- The `_tavily_search` function does not need to be changed — the fix belongs in `make_web_search_with_domains` because that is the factory responsible for converting user-supplied config into a ready-to-use tool.
- If Tavily's behavior with domain+path filters (`prozorro-api-docs.readthedocs.io/en/master`) is not as expected during manual testing, fall back to domain-only (`prozorro-api-docs.readthedocs.io`). This would only require updating `.env`, not the code.
- `docs/DELIVERY_CHECKLIST.md` Phase 2.3 integration test (`[ ] Integration test: technical query → Technical Support → sources cited`) should be checked after the manual smoke test passes.
