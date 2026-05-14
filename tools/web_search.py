"""Web search wrapper for current external procurement information.

We use TavilyClient directly because the installed LangChain Tavily wrapper
does not expose `language` / `country`, which are required by the architecture.
"""

from __future__ import annotations

from langchain_core.tools import tool
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from tavily import TavilyClient

from config import settings

_SEARCH_FALLBACK = "Результати не знайдено."


def _tavily_search(query: str, allowed_domains: list[str] | None = None) -> list[dict]:
    assert settings.tavily_api_key, "TAVILY_API_KEY required"
    client = TavilyClient(api_key=settings.tavily_api_key.get_secret_value())
    # Tavily applies the locale more reliably when both language and country are set.
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=5,
        language="uk",
        country="UA",
        include_domains=allowed_domains or None,
    )
    return response.get("results", [])


def _is_ukrainian(text: str) -> bool:
    try:
        return detect(text) == "uk"
    except LangDetectException:
        return False


def _format_results(
    results: list[dict],
    max_snippet: int = 500,
    require_ukrainian: bool = True,
) -> str:
    formatted_blocks: list[str] = []

    for result in results:
        content = str(result.get("content") or "").strip()
        if require_ukrainian and not _is_ukrainian(content):
            continue

        title = str(result.get("title") or "").strip()
        url = str(result.get("url") or "").strip()
        snippet = content[:max_snippet]
        if len(content) > max_snippet:
            snippet = f"{snippet}..."

        formatted_blocks.append(f"---\n{title}\n{snippet}\nДжерело: {url}")
        if len(formatted_blocks) == 5:
            break

    return "\n\n".join(formatted_blocks) if formatted_blocks else _SEARCH_FALLBACK


@tool
def web_search(query: str) -> str:
    """Пошук актуальної інформації про публічні закупівлі в Україні.

    Використовуй для нещодавніх змін, новин і зовнішніх джерел поза базою знань.
    Повертає тільки україномовні результати.
    """
    try:
        return _format_results(_tavily_search(query))
    except Exception:
        return _SEARCH_FALLBACK


def make_web_search_with_domains(allowed_domains: list[str]):
    locked_domains = [d.split("://", 1)[1] if "://" in d else d for d in allowed_domains]

    @tool("web_search_technical")
    def web_search_technical(query: str) -> str:
        """Пошук у мережі лише по погоджених джерелах Prozorro техпідтримки.

        Використовуй для технічних питань, коли потрібна актуальна зовнішня
        інформація лише з затверджених доменів.
        """
        try:
            # Whitelisted domains are explicitly trusted; skip language filter so
            # English technical docs (e.g. GitHub READMEs) are not silently dropped.
            return _format_results(
                _tavily_search(query, allowed_domains=locked_domains),
                require_ukrainian=False,
            )
        except Exception:
            return _SEARCH_FALLBACK

    return web_search_technical
