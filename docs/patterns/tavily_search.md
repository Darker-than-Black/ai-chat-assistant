# Tavily web search

## When to use

Web search inside an agent. Tavily is search-optimized for LLM consumption (clean snippets, ranked, no captchas) and has a generous free tier — chosen for this project over DuckDuckGo (`ddgs`) for reliability and over SerpAPI for cost.

In this project: `tools/web_search.py` wraps `TavilySearchResults` with our project-specific defaults (Ukrainian language, optional domain whitelist, post-filter for non-UA results).

## Minimal example

```python
from langchain_community.tools.tavily_search import TavilySearchResults

tavily_search = TavilySearchResults(
    max_results=5,
    search_depth="basic",                  # "basic" | "advanced"
    include_domains=None,                  # ["example.com", ...] for whitelist
    # exclude_domains=None,
    # include_answer=False,                # Tavily can synthesize a one-line answer
    # include_raw_content=False,           # full page content, expensive
)

results = tavily_search.invoke("як зареєструвати замовника в Prozorro")
# results: list[dict] with {"url": str, "content": str, "title": str, ...}
```

For our project, the wrapper enforces:
```python
TavilySearchResults(
    max_results=settings.web_search_max_results,
    search_depth="basic",
    include_domains=allowed_domains_or_none,   # whitelist for Technical Support
    # language=uk + country=UA passed via the Tavily SDK kwargs
)
```
…then a post-filter removes results whose `content` `langdetect`s as non-Ukrainian.

## Pitfalls

- **Language and country are SDK params, not query operators.** Don't try to enforce language by appending "in Ukrainian" to the query — pass `language="uk"` to the underlying client.
- **`search_depth="advanced"`** is ~3× slower and costs more credits but pulls cleaner snippets. Use only for the Critic's fact-checking step, not for routine workers.
- **`include_domains` is a hard filter.** If the whitelist excludes too many domains, you'll get zero results — handle the empty case in the calling agent (return `found=False`, don't crash).
- **Snippets are short** (Tavily's `content` is typically 1-3 sentences). For deep reading you'd need `read_url` (separate tool — `trafilatura` etc.) or `include_raw_content=True` (expensive).
- **Free-tier limits:** 1000 searches/month. Don't hammer the API in tests — mock it (see `tests/conftest.py` patterns).
- **Result schema differs slightly between Tavily versions.** If the wrapper changes its output format, verify keys (`url` vs `link`, `content` vs `snippet`).
- **Don't trust language filtering 100%.** Even with `language="uk"`, occasional Russian or English results slip through — keep the post-filter.

## Source

`lesson-8.md` (cells 19, 21 — `TavilySearchResults` integration).
