from types import SimpleNamespace
from unittest.mock import patch

import pytest

import tools.web_search as web_search_module
from tools.web_search import _SEARCH_FALLBACK, make_web_search_with_domains, web_search


@pytest.fixture
def tavily_api_key_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        web_search_module.settings,
        "tavily_api_key",
        SimpleNamespace(get_secret_value=lambda: "test-tavily-key"),
    )


def test_web_search_returns_ukrainian_only(tavily_api_key_stub: None) -> None:
    ukrainian_results = [
        {
            "title": "Оновлення Prozorro",
            "url": "https://prozorro.gov.ua/news/update-1",
            "content": "Міністерство економіки оприлюднило нові роз'яснення щодо публічних закупівель.",
        },
        {
            "title": "Роз'яснення для замовників",
            "url": "https://infobox.prozorro.org/articles/update-2",
            "content": "Замовникам нагадали про вимоги до тендерної документації та строків подання.",
        },
        {
            "title": "English procurement update",
            "url": "https://example.com/english-update",
            "content": "Public procurement guidance was updated for international readers.",
        },
    ]

    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {"results": ukrainian_results}

        result = web_search.invoke({"query": "оновлення закупівель"})

    assert "Оновлення Prozorro" in result
    assert "https://prozorro.gov.ua/news/update-1" in result
    assert "Роз'яснення для замовників" in result
    assert "https://infobox.prozorro.org/articles/update-2" in result
    assert "English procurement update" not in result
    assert "https://example.com/english-update" not in result


def test_web_search_passes_ukrainian_locale_to_tavily(
    tavily_api_key_stub: None,
) -> None:
    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {"results": []}

        web_search.invoke({"query": "оновлення закупівель"})

    assert mock_tavily_client.return_value.search.call_args.kwargs["language"] == "uk"
    assert mock_tavily_client.return_value.search.call_args.kwargs["country"] == "UA"


def test_web_search_drops_non_ukrainian_by_langdetect(tavily_api_key_stub: None) -> None:
    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {
            "results": [
                {
                    "title": "English only",
                    "url": "https://example.com/english",
                    "content": "Tender documentation changes were published in English only.",
                }
            ]
        }

        result = web_search.invoke({"query": "english procurement"})

    assert result == _SEARCH_FALLBACK


def test_web_search_with_domains_passes_include_domains(
    tavily_api_key_stub: None,
) -> None:
    restricted_search = make_web_search_with_domains(["prozorro.gov.ua"])

    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {
            "results": [
                {
                    "title": "Технічна підтримка",
                    "url": "https://prozorro.gov.ua/support",
                    "content": "Офіційна довідка Prozorro для користувачів електронної системи закупівель.",
                }
            ]
        }

        restricted_search.invoke({"query": "помилка кабінету"})

    assert mock_tavily_client.return_value.search.call_args.kwargs["include_domains"] == [
        "prozorro.gov.ua"
    ]


def test_web_search_with_domains_strips_url_scheme(
    tavily_api_key_stub: None,
) -> None:
    restricted_search = make_web_search_with_domains(
        [
            "https://prozorro-api-docs.readthedocs.io",
            "https://github.com",
        ]
    )

    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {"results": []}

        restricted_search.invoke({"query": "помилка API"})

    assert mock_tavily_client.return_value.search.call_args.kwargs["include_domains"] == [
        "prozorro-api-docs.readthedocs.io",
        "github.com",
    ]


def test_web_search_handles_tavily_exception(tavily_api_key_stub: None) -> None:
    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.side_effect = RuntimeError("tavily down")

        result = web_search.invoke({"query": "поточні зміни"})

    assert result == _SEARCH_FALLBACK


def test_web_search_technical_includes_non_ukrainian_from_whitelisted_domains(
    tavily_api_key_stub: None,
) -> None:
    restricted_search = make_web_search_with_domains(["github.com"])

    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {
            "results": [
                {
                    "title": "prozorro-eds README",
                    "url": "https://github.com/ProzorroUKR/prozorro-eds",
                    "content": "Electronic Document Signing service for Prozorro. Handles KEP integration.",
                }
            ]
        }

        result = restricted_search.invoke({"query": "prozorro-eds функції"})

    assert "prozorro-eds README" in result
    assert result != _SEARCH_FALLBACK


def test_web_search_snippet_truncation(tavily_api_key_stub: None) -> None:
    long_content = (
        "Це український текст про публічні закупівлі та тендерну документацію. " * 20
    ).strip()

    with patch("tools.web_search.TavilyClient") as mock_tavily_client:
        mock_tavily_client.return_value.search.return_value = {
            "results": [
                {
                    "title": "Довгий матеріал",
                    "url": "https://prozorro.gov.ua/long-read",
                    "content": long_content,
                }
            ]
        }

        result = web_search.invoke({"query": "довгий матеріал"})

    snippet = result.splitlines()[2]

    assert snippet == f"{long_content[:500]}..."
    assert snippet.endswith("...")
