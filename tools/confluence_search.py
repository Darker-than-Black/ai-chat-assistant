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
_MAX_EXCERPT_CHARS = 4000
_MAX_RESULTS = 3
_MAX_CONTEXT_CHARS = 12000


def _strip_html(html: str) -> str:
    # Remove HTML tags first, then CSS color-token garbage that Confluence embeds
    # as text content (e.g. "[data-colorid=abc]{color:#cc7832}").
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\[data-[^\]]+\]\{[^}]+\}", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _build_cql_text(query: str) -> str:
    # CQL text~"phrase" requires an exact phrase match; long LLM-generated queries
    # (synonym expansions) will never match verbatim. Instead, search title and text
    # for the first 3 meaningful tokens so any one match surfaces the page.
    tokens = [t.strip('"\'.,;:!?()[]') for t in query.split() if len(t) > 3][:3]
    if not tokens:
        tokens = query.split()[:2]
    primary = tokens[0]
    parts = [f'title~"{primary}"', f'text~"{primary}"']
    for term in tokens[1:]:
        parts.append(f'text~"{term}"')
    return " OR ".join(parts)


def _search_confluence(query: str) -> list[dict]:
    assert settings.confluence_url, "CONFLUENCE_URL required"
    assert settings.confluence_username, "CONFLUENCE_USERNAME required"
    assert settings.confluence_api_token, "CONFLUENCE_API_TOKEN required"

    cql = f"({_build_cql_text(query)}) AND type=page"
    if settings.confluence_space_keys:
        keys = ",".join(settings.confluence_space_keys)
        cql += f" AND space.key IN ({keys})"

    resp = httpx.get(
        f"{settings.confluence_url}/rest/api/content/search",
        params={
            "cql": cql,
            "limit": _MAX_RESULTS,
            "expand": "body.view,version",
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
        # version.when is ISO-8601; include as "Дата: ..." for Critic freshness check
        updated = page.get("version", {}).get("when", "")
        date_line = f"Дата: {updated[:10]}\n" if updated else ""
        raw_html = page.get("body", {}).get("view", {}).get("value", "")
        text = _strip_html(raw_html)
        excerpt = text[:_MAX_EXCERPT_CHARS]
        if len(text) > _MAX_EXCERPT_CHARS:
            excerpt = f"{excerpt}..."
        blocks.append(f"---\n{title}\n{date_line}{excerpt}\nДжерело: {url}")
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
