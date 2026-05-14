"""Tool correctness tests: agents are wired to the right tools.

Verifies the tool-routing invariants from CLAUDE.md / ARCHITECTURE § 6:
  - Lawyer uses ONLY rag_search (laws collection by default)
  - Common Support uses rag_search (articles) + plain web_search (no domain whitelist)
  - Technical Support uses rag_search (articles, tag-whitelisted) + web_search (with allowed_domains)
  - Web search filters non-Ukrainian results
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agents.common_support import build_common_support_agent
from agents.lawyer import build_lawyer_agent
from agents.technical_support import build_technical_support_agent
from config import settings
from tools.rag import make_rag_search_articles, rag_search
from tools.web_search import _format_results, make_web_search_with_domains


# ─────────────────────────────────────────────────────────────────
# Lawyer wiring
# ─────────────────────────────────────────────────────────────────

def test_lawyer_uses_only_rag_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lawyer must NOT have web_search; only the global rag_search tool."""
    captured: dict = {}

    def fake_create_react_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="lawyer-agent")

    monkeypatch.setattr("agents.lawyer.create_react_agent", fake_create_react_agent)
    monkeypatch.setattr("agents.lawyer.get_llm", lambda: object())

    build_lawyer_agent()

    tools = captured["tools"]
    assert len(tools) == 1
    assert tools[0] is rag_search
    assert tools[0].name == "rag_search"


def test_rag_search_defaults_to_laws_collection() -> None:
    """rag_search defaults to collection='laws' so the Lawyer never hits articles by accident."""
    schema = rag_search.args_schema.model_json_schema()
    assert schema["properties"]["collection"]["default"] == "laws"


# ─────────────────────────────────────────────────────────────────
# Common Support wiring
# ─────────────────────────────────────────────────────────────────

def test_common_support_uses_rag_articles_and_unfiltered_web_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Common Support has rag_search (articles) + web_search WITHOUT allowed_domains."""
    rag_tool = SimpleNamespace(name="rag_search_articles")
    captured: dict = {}

    def fake_create_react_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="common-support-agent")

    monkeypatch.setattr(
        "agents.common_support.make_rag_search_articles",
        Mock(return_value=rag_tool),
    )
    monkeypatch.setattr(
        "agents.common_support.create_react_agent", fake_create_react_agent
    )
    monkeypatch.setattr("agents.common_support.get_llm", lambda: object())

    build_common_support_agent()

    tools = captured["tools"]
    assert len(tools) == 2
    assert tools[0] is rag_tool
    assert tools[1].name == "web_search"


# ─────────────────────────────────────────────────────────────────
# Technical Support wiring
# ─────────────────────────────────────────────────────────────────

def test_technical_support_applies_tag_whitelist_and_domain_whitelist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Technical Support gets a tag-restricted RAG tool and a domain-restricted web search."""
    rag_tool = SimpleNamespace(name="rag_search_articles")
    web_tool = SimpleNamespace(name="web_search_technical")
    captured: dict = {}

    rag_factory = Mock(return_value=rag_tool)
    web_factory = Mock(return_value=web_tool)

    def fake_create_react_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="technical-support-agent")

    monkeypatch.setattr(
        "agents.technical_support.make_rag_search_articles", rag_factory
    )
    monkeypatch.setattr(
        "agents.technical_support.make_web_search_with_domains", web_factory
    )
    monkeypatch.setattr(
        "agents.technical_support.create_react_agent", fake_create_react_agent
    )
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: object())

    monkeypatch.setattr(settings, "tech_support_tag_whitelist", ["tutorial", "kep"])
    monkeypatch.setattr(
        settings, "tech_support_allowed_domains", ["prozorro.gov.ua", "me.gov.ua"]
    )
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)

    build_technical_support_agent()

    rag_factory.assert_called_once_with(tag_whitelist=["tutorial", "kep"])
    web_factory.assert_called_once_with(["prozorro.gov.ua", "me.gov.ua"])
    assert captured["tools"][:2] == [rag_tool, web_tool]
    assert captured["tools"][2].name == "confluence_search"


def test_technical_support_falls_back_to_plain_web_search_when_no_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty allowed_domains → use the unfiltered web_search instead of the wrapper."""
    rag_tool = SimpleNamespace(name="rag_search_articles")
    captured: dict = {}

    web_factory = Mock()  # MUST NOT be called

    def fake_create_react_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="technical-support-agent")

    monkeypatch.setattr(
        "agents.technical_support.make_rag_search_articles",
        Mock(return_value=rag_tool),
    )
    monkeypatch.setattr(
        "agents.technical_support.make_web_search_with_domains", web_factory
    )
    monkeypatch.setattr(
        "agents.technical_support.create_react_agent", fake_create_react_agent
    )
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: object())
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)

    build_technical_support_agent()

    web_factory.assert_not_called()
    assert captured["tools"][1].name == "web_search"


# ─────────────────────────────────────────────────────────────────
# RAG tool dispatching
# ─────────────────────────────────────────────────────────────────

def test_rag_search_dispatches_to_hybrid_with_chosen_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared rag_search tool forwards the selected collection to hybrid_search."""
    captured: dict = {}

    def fake_hybrid_search(query, collection, top_k=5, **kwargs):
        captured["query"] = query
        captured["collection"] = collection
        captured["top_k"] = top_k
        return []

    monkeypatch.setattr("tools.rag.hybrid_search", fake_hybrid_search)

    rag_search.invoke({"query": "стаття 164-14", "collection": "laws"})

    assert captured["query"] == "стаття 164-14"
    assert captured["collection"] == "laws"


def test_make_rag_search_articles_forwards_tag_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """make_rag_search_articles wraps hybrid_search with the tag filter applied."""
    captured: dict = {}

    def fake_hybrid_search(query, collection, filters=None, top_k=5):
        captured["collection"] = collection
        captured["filters"] = filters
        return []

    monkeypatch.setattr("tools.rag.hybrid_search", fake_hybrid_search)

    tool = make_rag_search_articles(tag_whitelist=["tutorial", "interface"])
    tool.invoke({"query": "як завантажити документ"})

    assert captured["collection"] == "articles"
    assert captured["filters"] == {"tags": ["tutorial", "interface"]}


def test_make_rag_search_articles_no_filter_when_no_whitelist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_hybrid_search(query, collection, filters=None, top_k=5):
        captured["filters"] = filters
        return []

    monkeypatch.setattr("tools.rag.hybrid_search", fake_hybrid_search)

    tool = make_rag_search_articles(tag_whitelist=None)
    tool.invoke({"query": "загальне питання"})

    assert captured["filters"] is None


# ─────────────────────────────────────────────────────────────────
# Web search filters
# ─────────────────────────────────────────────────────────────────

def test_web_search_drops_non_ukrainian_results() -> None:
    """Tavily can return mixed-language results; we keep only Ukrainian ones."""
    results = [
        {
            "title": "UA result",
            "content": "Це україномовний контент про публічні закупівлі та Prozorro.",
            "url": "https://example.ua",
        },
        {
            "title": "EN result",
            "content": "This is English content about procurement and tender procedures.",
            "url": "https://example.com",
        },
    ]

    formatted = _format_results(results)

    assert "україномовний контент" in formatted
    assert "English content" not in formatted
    assert "https://example.com" not in formatted


def test_web_search_with_domains_passes_whitelist_to_tavily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """make_web_search_with_domains injects allowed_domains into the Tavily call."""
    captured: dict = {}

    def fake_tavily_search(query, allowed_domains=None):
        captured["query"] = query
        captured["allowed_domains"] = allowed_domains
        return []

    monkeypatch.setattr("tools.web_search._tavily_search", fake_tavily_search)

    tool_fn = make_web_search_with_domains(["prozorro.gov.ua", "me.gov.ua"])
    tool_fn.invoke({"query": "помилка КЕП"})

    assert captured["allowed_domains"] == ["prozorro.gov.ua", "me.gov.ua"]
    assert tool_fn.name == "web_search_technical"
