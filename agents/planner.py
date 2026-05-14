"""Planner agent: classify procurement-support queries into a multi-topic ResearchPlan."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.lawyer import get_llm
from config import settings
from observability.langfuse_client import load_prompt
from schemas import ResearchPlan

_MAX_SUBTASKS_PLACEHOLDER = "__PLANNER_MAX_SUBTASKS__"


def _load_system_prompt() -> str:
    prompt = load_prompt(name="procurement-planner")
    return prompt.replace(
        _MAX_SUBTASKS_PLACEHOLDER,
        str(settings.planner_max_subtasks),
    )


def _normalize_plan(plan: ResearchPlan) -> ResearchPlan:
    if plan.needs_human and plan.subtasks:
        return plan.model_copy(update={"subtasks": []})
    if len(plan.subtasks) > settings.planner_max_subtasks:
        return plan.model_copy(
            update={"subtasks": plan.subtasks[: settings.planner_max_subtasks]}
        )
    return plan


def invoke_planner(query: str) -> ResearchPlan:
    llm = get_llm().with_structured_output(ResearchPlan)
    plan = llm.invoke(
        [
            SystemMessage(content=_load_system_prompt()),
            HumanMessage(content=query),
        ]
    )
    return _normalize_plan(plan)
