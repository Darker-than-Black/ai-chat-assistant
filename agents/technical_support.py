"""Technical Support worker for Prozorro platform and procedural support queries."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from agents.lawyer import get_llm
from config import settings
from schemas import WorkerResponse
from tools.confluence_search import confluence_search
from tools.github_repo_search import github_repo_search
from tools.rag import make_rag_search_articles
from tools.web_search import make_web_search_with_domains, web_search
from observability.langfuse_client import load_prompt


def _load_system_prompt() -> str:
    return load_prompt(name="procurement-technical-support")


def build_technical_support_agent():  # type: ignore[return]
    tag_whitelist = settings.tech_support_tag_whitelist or None
    allowed_domains = settings.tech_support_allowed_domains
    rag_tool = make_rag_search_articles(tag_whitelist=tag_whitelist)
    web_tool = (
        make_web_search_with_domains(allowed_domains)
        if allowed_domains
        else web_search
    )
    return create_react_agent(
        model=get_llm(),
        tools=[rag_tool, web_tool, confluence_search, github_repo_search],
        prompt=_load_system_prompt(),
        response_format=WorkerResponse,
    )


_technical_support = None


def get_technical_support_agent():  # type: ignore[return]
    global _technical_support
    if _technical_support is None:
        _technical_support = build_technical_support_agent()
    return _technical_support


def invoke_technical_support(
    query: str, revision_feedback: str | None = None
) -> WorkerResponse:
    if revision_feedback:
        query = f"[REVISION REQUEST]: {revision_feedback}\n\n[ORIGINAL QUERY]: {query}"
    result = get_technical_support_agent().invoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["structured_response"]


def technical_support_node(state: dict) -> dict:
    subtask = state["subtask"]
    feedback = state.get("revision_feedback")
    return {
        "worker_responses": [
            invoke_technical_support(subtask.query, revision_feedback=feedback)
        ]
    }
