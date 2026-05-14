from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agents.common_support import build_common_support_agent, invoke_common_support
from schemas import WorkerResponse


@pytest.fixture
def mock_worker_response_common() -> WorkerResponse:
    return WorkerResponse(
        topic="procurement_general",
        found=True,
        answer="Загальна консультація щодо закупівель.",
        confidence=0.86,
    )


def _mock_agent(response: WorkerResponse) -> Mock:
    agent = Mock()
    agent.invoke.return_value = {"structured_response": response}
    return agent


def test_invoke_common_support_returns_worker_response(
    monkeypatch: pytest.MonkeyPatch,
    mock_worker_response_common: WorkerResponse,
) -> None:
    mock_agent = _mock_agent(mock_worker_response_common)
    monkeypatch.setattr(
        "agents.common_support.get_common_support_agent",
        lambda: mock_agent,
    )

    result = invoke_common_support("Що таке спрощена закупівля?")

    assert result is mock_worker_response_common


def test_common_support_topic_is_procurement_general(
    monkeypatch: pytest.MonkeyPatch,
    mock_worker_response_common: WorkerResponse,
) -> None:
    mock_agent = _mock_agent(mock_worker_response_common)
    monkeypatch.setattr(
        "agents.common_support.get_common_support_agent",
        lambda: mock_agent,
    )

    result = invoke_common_support("Поясни етапи відкритих торгів")

    assert result is mock_worker_response_common
    assert result.topic == "procurement_general"


def test_common_support_not_found_returns_found_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    not_found_response = WorkerResponse(
        topic="procurement_general",
        found=False,
        answer="Не вдалося знайти релевантну інформацію в наявних джерелах.",
        confidence=0.18,
    )
    mock_agent = _mock_agent(not_found_response)
    monkeypatch.setattr(
        "agents.common_support.get_common_support_agent",
        lambda: mock_agent,
    )

    result = invoke_common_support("Невідомий виняток у процедурі закупівлі")

    assert result is not_found_response
    assert result.topic == "procurement_general"
    assert result.found is False


def test_build_common_support_agent_uses_articles_rag_and_web_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rag_tool = object()
    llm = object()
    created_agent = SimpleNamespace(name="common-support-agent")
    make_rag_search_articles = Mock(return_value=rag_tool)
    create_react_agent = Mock(return_value=created_agent)

    monkeypatch.setattr(
        "agents.common_support.make_rag_search_articles",
        make_rag_search_articles,
    )
    monkeypatch.setattr(
        "agents.common_support.create_react_agent",
        create_react_agent,
    )
    monkeypatch.setattr("agents.common_support.get_llm", lambda: llm)

    result = build_common_support_agent()

    assert result is created_agent
    make_rag_search_articles.assert_called_once_with()
    create_react_agent.assert_called_once_with(
        model=llm,
        tools=[rag_tool, create_react_agent.call_args.kwargs["tools"][1]],
        prompt=create_react_agent.call_args.kwargs["prompt"],
        response_format=WorkerResponse,
    )
    assert create_react_agent.call_args.kwargs["tools"][1].name == "web_search"
