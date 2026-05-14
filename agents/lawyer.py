"""Lawyer agent: legal domain specialist for Ukrainian procurement law."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import settings
from schemas import WorkerResponse
from tools.rag import rag_search
from observability.langfuse_client import load_prompt


class OpenAIFunctionCallingChat(ChatOpenAI):
    """Force OpenAI structured output onto function-calling for schemas with free-form metadata."""

    def with_structured_output(self, schema=None, **kwargs):
        kwargs.setdefault("method", "function_calling")
        return super().with_structured_output(schema, **kwargs)


def get_llm() -> BaseChatModel:
    if settings.llm_provider == "openai":
        assert settings.openai_api_key, "OPENAI_API_KEY required"
        return OpenAIFunctionCallingChat(
            model=settings.llm_model,
            api_key=settings.openai_api_key.get_secret_value(),
            temperature=0,
        )
    assert settings.anthropic_api_key, "ANTHROPIC_API_KEY required"
    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key.get_secret_value(),
        temperature=0,
    )


def _load_system_prompt() -> str:
    return load_prompt(name="procurement-lawyer")


def build_lawyer_agent():  # type: ignore[return]
    return create_react_agent(
        model=get_llm(),
        tools=[rag_search],
        prompt=_load_system_prompt(),
        response_format=WorkerResponse,
    )


_lawyer = None


def get_lawyer_agent():  # type: ignore[return]
    global _lawyer
    if _lawyer is None:
        _lawyer = build_lawyer_agent()
    return _lawyer


def invoke_lawyer(query: str, revision_feedback: str | None = None) -> WorkerResponse:
    if revision_feedback:
        query = f"[REVISION REQUEST]: {revision_feedback}\n\n[ORIGINAL QUERY]: {query}"
    result = get_lawyer_agent().invoke(
        {"messages": [HumanMessage(content=query)]}
    )
    return result["structured_response"]


def lawyer_node(state: dict) -> dict:
    subtask = state["subtask"]
    feedback = state.get("revision_feedback")
    return {"worker_responses": [invoke_lawyer(subtask.query, revision_feedback=feedback)]}
