"""Common Support worker for general procurement guidance and current public info."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from agents.lawyer import get_llm
from schemas import WorkerResponse
from tools.rag import make_rag_search_articles
from tools.web_search import web_search
from observability.langfuse_client import load_prompt


def _load_system_prompt() -> str:
    return load_prompt(name="procurement-common-support")


def build_common_support_agent():  # type: ignore[return]
    return create_react_agent(
        model=get_llm(),
        tools=[make_rag_search_articles(), web_search],
        prompt=_load_system_prompt(),
        response_format=WorkerResponse,
    )


_common_support = None


def get_common_support_agent():  # type: ignore[return]
    global _common_support
    if _common_support is None:
        _common_support = build_common_support_agent()
    return _common_support


def invoke_common_support(
    query: str, revision_feedback: str | None = None
) -> WorkerResponse:
    if revision_feedback:
        query = f"[REVISION REQUEST]: {revision_feedback}\n\n[ORIGINAL QUERY]: {query}"
    result = get_common_support_agent().invoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["structured_response"]


def common_support_node(state: dict) -> dict:
    subtask = state["subtask"]
    feedback = state.get("revision_feedback")
    return {
        "worker_responses": [
            invoke_common_support(subtask.query, revision_feedback=feedback)
        ]
    }
