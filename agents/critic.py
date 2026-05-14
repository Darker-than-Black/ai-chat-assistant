"""Critic agent: evaluates aggregated response quality across Freshness/Completeness/Structure."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.lawyer import get_llm
from config import settings
from observability.langfuse_client import load_prompt
from schemas import CritiqueResult, GraphState, ResearchPlan, WorkerResponse


def _load_system_prompt() -> str:
    return load_prompt(
        name="procurement-critic",
        laws_threshold=settings.laws_freshness_threshold_days,
        articles_threshold=settings.articles_freshness_threshold_days,
    )


def invoke_critic(
    aggregated_response: str,
    plan: ResearchPlan,
    worker_responses: list[WorkerResponse],
) -> CritiqueResult:
    llm = get_llm().with_structured_output(CritiqueResult)
    system = _load_system_prompt()
    human = (
        f"## Оригінальний запит\n{plan.original_query}\n\n"
        f"## План дослідження\n{plan.model_dump_json(indent=2)}\n\n"
        f"## Агрегована відповідь агентів\n{aggregated_response}\n\n"
        f"## Метадані агентів\n"
        + "\n".join(
            f"- {r.topic}: found={r.found}, confidence={r.confidence}"
            for r in worker_responses
        )
    )
    return llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])


def critic_node(state: GraphState) -> dict:
    critique = invoke_critic(
        aggregated_response=state.get("aggregated_response") or "",
        plan=state["plan"],
        worker_responses=state["worker_responses"],
    )
    return {
        "critic_history": state["critic_history"] + [critique],
        "retry_count": state["retry_count"] + 1,
    }
