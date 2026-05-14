from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import HumanMessage

from agents.technical_support import (
    build_technical_support_agent,
    invoke_technical_support,
)
from config import settings
from schemas import WorkerResponse
from tools.confluence_search import confluence_search as _confluence_search_tool
from tools.github_repo_search import github_repo_search as _github_repo_search_tool


def test_invoke_technical_support_returns_worker_response(monkeypatch) -> None:
    expected = WorkerResponse(
        topic="technical_system",
        found=True,
        answer="Перевірте формат файлу та повторіть завантаження.",
        confidence=0.87,
    )
    agent = Mock()
    agent.invoke.return_value = {"structured_response": expected}
    monkeypatch.setattr(
        "agents.technical_support.get_technical_support_agent",
        lambda: agent,
    )

    result = invoke_technical_support("Не завантажується документ у систему")

    assert result == expected
    agent.invoke.assert_called_once()
    payload = agent.invoke.call_args.args[0]
    assert len(payload["messages"]) == 1
    assert isinstance(payload["messages"][0], HumanMessage)
    assert payload["messages"][0].content == "Не завантажується документ у систему"


def test_technical_support_topic_is_technical_system(monkeypatch) -> None:
    expected = WorkerResponse(
        topic="technical_system",
        found=True,
        answer="Оновіть сторінку та перевірте статус майданчика.",
        confidence=0.74,
    )
    agent = Mock()
    agent.invoke.return_value = {"structured_response": expected}
    monkeypatch.setattr(
        "agents.technical_support.get_technical_support_agent",
        lambda: agent,
    )

    result = invoke_technical_support("Чому зависає сторінка подання пропозиції?")

    assert result.topic == "technical_system"


def test_technical_support_bug_report_sets_needs_human(monkeypatch) -> None:
    expected = WorkerResponse(
        topic="technical_system",
        found=False,
        answer="Проблему потрібно передати технічному спеціалісту.",
        confidence=0.22,
        needs_human=True,
        needs_human_reason="Потрібна перевірка інциденту та логів майданчика.",
    )
    agent = Mock()
    agent.invoke.return_value = {"structured_response": expected}
    monkeypatch.setattr(
        "agents.technical_support.get_technical_support_agent",
        lambda: agent,
    )

    result = invoke_technical_support("Після підписання КЕП система повертає невідому помилку 500.")

    assert result.needs_human is True
    assert result.needs_human_reason


def test_technical_support_rag_tool_uses_tag_whitelist(monkeypatch) -> None:
    rag_tool = object()
    web_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    make_web_search_with_domains = Mock(return_value=web_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr(
        "agents.technical_support.make_rag_search_articles",
        make_rag_search_articles,
    )
    monkeypatch.setattr(
        "agents.technical_support.make_web_search_with_domains",
        make_web_search_with_domains,
    )
    monkeypatch.setattr(
        "agents.technical_support.create_react_agent",
        create_react_agent,
    )
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(
        settings,
        "tech_support_tag_whitelist",
        ["kep", "errors", "bid-submission"],
    )
    monkeypatch.setattr(
        settings,
        "tech_support_allowed_domains",
        ["prozorro.gov.ua", "infobox.prozorro.org"],
    )
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)
    monkeypatch.setattr(settings, "tech_support_github_repos", [])

    result = build_technical_support_agent()

    assert result is created_agent
    make_rag_search_articles.assert_called_once_with(
        tag_whitelist=["kep", "errors", "bid-submission"]
    )
    make_web_search_with_domains.assert_called_once_with(
        ["prozorro.gov.ua", "infobox.prozorro.org"]
    )
    create_react_agent.assert_called_once_with(
        model=llm,
        tools=[rag_tool, web_tool, _confluence_search_tool, _github_repo_search_tool],
        prompt=create_react_agent.call_args.kwargs["prompt"],
        response_format=WorkerResponse,
    )


def test_technical_support_falls_back_to_plain_web_search_without_domains(
    monkeypatch,
) -> None:
    rag_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    make_web_search_with_domains = Mock()
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr(
        "agents.technical_support.make_rag_search_articles",
        make_rag_search_articles,
    )
    monkeypatch.setattr(
        "agents.technical_support.make_web_search_with_domains",
        make_web_search_with_domains,
    )
    monkeypatch.setattr(
        "agents.technical_support.create_react_agent",
        create_react_agent,
    )
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)
    monkeypatch.setattr(settings, "tech_support_github_repos", [])

    result = build_technical_support_agent()

    assert result is created_agent
    make_rag_search_articles.assert_called_once_with(tag_whitelist=None)
    make_web_search_with_domains.assert_not_called()
    assert create_react_agent.call_args.kwargs["tools"][1].name == "web_search"


def test_technical_support_includes_confluence_when_configured(monkeypatch) -> None:
    rag_tool = object()
    web_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    make_web_search_with_domains = Mock(return_value=web_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
    monkeypatch.setattr("agents.technical_support.make_web_search_with_domains", make_web_search_with_domains)
    monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", ["prozorro.gov.ua"])
    monkeypatch.setattr(settings, "confluence_url", "https://acme.atlassian.net/wiki")
    monkeypatch.setattr(
        settings,
        "confluence_api_token",
        SimpleNamespace(get_secret_value=lambda: "tok"),
    )
    monkeypatch.setattr(settings, "tech_support_github_repos", [])

    build_technical_support_agent()

    tools_arg = create_react_agent.call_args.kwargs["tools"]
    assert len(tools_arg) == 4
    assert tools_arg[2].name == "confluence_search"


def test_technical_support_always_includes_confluence_and_github(monkeypatch) -> None:
    rag_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
    monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)
    monkeypatch.setattr(settings, "tech_support_github_repos", [])

    build_technical_support_agent()

    tools_arg = create_react_agent.call_args.kwargs["tools"]
    assert len(tools_arg) == 4
    assert tools_arg[2].name == "confluence_search"
    assert tools_arg[3] is _github_repo_search_tool


def test_technical_support_binds_github_repo_search_when_repos_configured(
    monkeypatch,
) -> None:
    rag_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
    monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)
    monkeypatch.setattr(settings, "tech_support_github_repos", ["ProzorroUKR/prozorro-eds"])

    build_technical_support_agent()

    tools_arg = create_react_agent.call_args.kwargs["tools"]
    assert len(tools_arg) == 4
    assert tools_arg[3] is _github_repo_search_tool


def test_technical_support_github_repo_search_always_bound(
    monkeypatch,
) -> None:
    """github_repo_search is always in the tool list; graceful degradation is
    handled by the tool itself returning a fallback when repos are unconfigured."""
    rag_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="technical-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr("agents.technical_support.make_rag_search_articles", make_rag_search_articles)
    monkeypatch.setattr("agents.technical_support.create_react_agent", create_react_agent)
    monkeypatch.setattr("agents.technical_support.get_llm", lambda: llm)
    monkeypatch.setattr(settings, "tech_support_tag_whitelist", [])
    monkeypatch.setattr(settings, "tech_support_allowed_domains", [])
    monkeypatch.setattr(settings, "confluence_url", None)
    monkeypatch.setattr(settings, "confluence_api_token", None)
    monkeypatch.setattr(settings, "tech_support_github_repos", [])

    build_technical_support_agent()

    tools_arg = create_react_agent.call_args.kwargs["tools"]
    assert _github_repo_search_tool in tools_arg
