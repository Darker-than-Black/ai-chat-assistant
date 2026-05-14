"""GitHub code search tool for public Prozorro repository documentation.

Uses the GitHub REST Search API with repo: qualifiers because Tavily does not support
repo-scoped code search — domain filtering is coarser than owner/repo scoping and
conflates web indexing with source-code search.
"""

from __future__ import annotations

import re

import httpx
from langchain_core.tools import tool

from config import settings

_FALLBACK = "Результатів пошуку в репозиторіях GitHub не знайдено."
_MAX_RESULTS = 5
_MAX_SNIPPET_CHARS = 400
_MAX_CONTEXT_CHARS = 8000
_GITHUB_SEARCH_URL = "https://api.github.com/search/code"


def _build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.text-match+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_api_token:
        headers["Authorization"] = f"Bearer {settings.github_api_token.get_secret_value()}"
    return headers


def _sanitize_query(query: str) -> str:
    # Strip user-supplied repo: qualifiers to prevent escaping the allowlist.
    return re.sub(r"\brepo:\S+", "", query).strip()


def _build_query(query: str, repos: list[str]) -> str:
    safe_query = _sanitize_query(query)
    repo_qualifiers = " ".join(f"repo:{r}" for r in repos)
    return f"{safe_query} {repo_qualifiers}"


def _search_github_repos(query: str, repos: list[str]) -> list[dict]:
    resp = httpx.get(
        _GITHUB_SEARCH_URL,
        params={"q": _build_query(query, repos), "per_page": _MAX_RESULTS},
        headers=_build_headers(),
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def _format_results(items: list[dict]) -> str:
    blocks = []
    for item in items:
        repo_name = item.get("repository", {}).get("full_name", "")
        path = item.get("path", "")
        html_url = item.get("html_url", "")

        text_matches = item.get("text_matches", [])
        snippet = ""
        if text_matches:
            fragment = text_matches[0].get("fragment", "")
            snippet = fragment[:_MAX_SNIPPET_CHARS]
            if len(fragment) > _MAX_SNIPPET_CHARS:
                snippet = f"{snippet}..."

        lines = [f"---", f"Репозиторій: {repo_name}", f"Файл: {path}"]
        if snippet:
            lines.append(snippet)
        lines.append(f"Джерело: {html_url}")
        blocks.append("\n".join(lines))

        if len(blocks) == _MAX_RESULTS:
            break

    context = "\n\n".join(blocks)
    return context[:_MAX_CONTEXT_CHARS] if len(context) > _MAX_CONTEXT_CHARS else context


@tool
def github_repo_search(query: str) -> str:
    """Search allowlisted GitHub repositories for Prozorro library docs and code examples.

    Use for questions about prozorro-eds, prozorro-pdf, and other ProzorroUKR public
    libraries: API methods, integration examples, README content, and code samples.
    Searches only inside repositories configured in TECH_SUPPORT_GITHUB_REPOS.
    Prefer this over web_search_technical for repo-specific documentation and code.
    """
    repos = settings.tech_support_github_repos
    if not repos:
        return _FALLBACK
    try:
        items = _search_github_repos(query, repos)
        if not items:
            return _FALLBACK
        return _format_results(items)
    except Exception:
        return _FALLBACK
