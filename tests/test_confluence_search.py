from types import SimpleNamespace
from unittest.mock import patch

import pytest

import tools.confluence_search as confluence_module
from tools.confluence_search import (
    _FALLBACK,
    _build_cql_text,
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


def _page(title: str, webui: str, html: str, updated: str = "") -> dict:
    page: dict = {"title": title, "_links": {"webui": webui}, "body": {"view": {"value": html}}}
    if updated:
        page["version"] = {"when": updated}
    return page


def test_confluence_search_returns_formatted_results(confluence_settings_stub: None) -> None:
    pages = [_page("API Guide", "/pages/1", "<p>Інструкція з інтеграції</p>", "2026-04-01T10:00:00.000Z")]
    with patch("tools.confluence_search.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": pages}
        mock_get.return_value.raise_for_status.return_value = None
        result = confluence_search.invoke({"query": "API інтеграція"})
    assert "API Guide" in result
    assert "Інструкція з інтеграції" in result
    assert "https://acme.atlassian.net/wiki/pages/1" in result
    assert "Дата: 2026-04-01" in result


def test_confluence_search_includes_date_when_version_present(confluence_settings_stub: None) -> None:
    pages = [_page("Guide", "/pages/9", "<p>Текст</p>", "2025-12-31T08:00:00.000Z")]
    with patch("tools.confluence_search.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": pages}
        mock_get.return_value.raise_for_status.return_value = None
        result = confluence_search.invoke({"query": "guide"})
    assert "Дата: 2025-12-31" in result


def test_confluence_search_omits_date_when_version_absent(confluence_settings_stub: None) -> None:
    pages = [_page("Guide", "/pages/10", "<p>Текст</p>")]
    with patch("tools.confluence_search.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": pages}
        mock_get.return_value.raise_for_status.return_value = None
        result = confluence_search.invoke({"query": "guide"})
    assert "Дата:" not in result


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
    # CQL must still be token-based, not a long phrase
    assert 'text~"test"' in cql


def test_confluence_search_no_space_filter_when_empty(confluence_settings_stub: None) -> None:
    with patch("tools.confluence_search.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status.return_value = None
        confluence_search.invoke({"query": "test"})
    cql = mock_get.call_args.kwargs["params"]["cql"]
    assert "space.key" not in cql


def test_strip_html_removes_all_tags() -> None:
    result = _strip_html("<h1>Title</h1><p>Body</p>")
    assert "Title" in result
    assert "Body" in result
    assert "<" not in result
    assert _strip_html("No tags") == "No tags"
    assert _strip_html("") == ""


def test_strip_html_removes_confluence_css_tokens() -> None:
    html = "[data-colorid=abc123]{color:#cc7832} html[data-color-mode=dark] [data-colorid=abc123]{color:#cd7933} Actual content here"
    result = _strip_html(html)
    assert "data-colorid" not in result
    assert "color:#cc7832" not in result
    assert "Actual content here" in result


def test_build_cql_text_uses_token_search_not_phrase() -> None:
    cql = _build_cql_text("prozorro-eds сервіс призначення функціональні можливості")
    # must NOT be a single phrase — that fails for long LLM-generated queries
    assert 'text~"prozorro-eds сервіс призначення' not in cql
    # primary term must appear in title and text search
    assert 'title~"prozorro-eds"' in cql
    assert 'text~"prozorro-eds"' in cql


def test_build_cql_text_short_query_still_works() -> None:
    cql = _build_cql_text("prozorro-eds")
    assert 'title~"prozorro-eds"' in cql
    assert 'text~"prozorro-eds"' in cql
