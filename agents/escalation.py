"""Escalation agent: LLM summary + audit file + Slack expert-channel notification."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from agents.lawyer import get_llm
from config import settings
from language import get_escalation_message
from observability.langfuse_client import load_prompt
from schemas import EscalationOutput, GraphState

def _load_system_prompt() -> str:
    return load_prompt(name="procurement-escalation")


def _determine_category(
    state: GraphState,
) -> Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]:
    # Critic-exhaustion path is unambiguous
    if state.get("retry_count", 0) >= settings.critic_max_retries and state.get("critic_history"):
        return "max_retries_exceeded"
    # Worker-signal path: check needs_human_reason for domain hints
    for resp in state.get("worker_responses", []):
        if resp.needs_human and resp.needs_human_reason:
            reason_lower = resp.needs_human_reason.lower()
            if any(kw in reason_lower for kw in ["баг", "bug", "помилка", "error", "збій"]):
                return "bug"
            if any(kw in reason_lower for kw in ["функці", "feature", "відсутн", "додати"]):
                return "feature_request"
    # Planner-gate path and everything else
    return "unanswerable"


def _build_attempted_resolution(state: GraphState) -> str:
    worker_responses = state.get("worker_responses", [])
    if not worker_responses:
        return "Запит не оброблявся агентами (пряма ескалація планером)."

    lines: list[str] = []
    for resp in worker_responses:
        status = "знайдено" if resp.found else "не знайдено"
        line = f"- {resp.topic}: {status}, впевненість={resp.confidence:.1f}"
        if resp.needs_human and resp.needs_human_reason:
            line += f", потрібна людина: {resp.needs_human_reason}"
        lines.append(line)

    critic_history = state.get("critic_history", [])
    if critic_history:
        last = critic_history[-1]
        lines.append(
            f"- Критик: {last.verdict}, повторів={state.get('retry_count', 0)}"
        )
        if last.gaps:
            lines.append(f"  Прогалини: {'; '.join(last.gaps[:3])}")

    return "\n".join(lines)


def _build_full_context(state: GraphState) -> dict:
    return {
        "plan": state["plan"].model_dump() if state.get("plan") else None,
        "worker_responses": [r.model_dump() for r in state.get("worker_responses", [])],
        "critic_history": [c.model_dump() for c in state.get("critic_history", [])],
        "retry_count": state.get("retry_count", 0),
    }


def _generate_summary(state: GraphState, category: str, attempted_resolution: str) -> str:
    plan = state.get("plan")
    escalation_reason = (
        plan.escalation_reason if plan and plan.escalation_reason else "Причина не вказана"
    )
    human = (
        f"## Запит користувача\n{state['user_message']}\n\n"
        f"## Категорія ескалації\n{category}\n\n"
        f"## Причина ескалації\n{escalation_reason}\n\n"
        f"## Результати агентів\n{attempted_resolution}\n"
    )
    result = get_llm().invoke([
        SystemMessage(content=_load_system_prompt()),
        HumanMessage(content=human),
    ])
    return result.content if hasattr(result, "content") else str(result)


def _save_to_file(escalation: EscalationOutput) -> None:
    output_dir = Path("output/escalations")
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_session = escalation.session_id.replace(":", "_")
    safe_ts = escalation.timestamp.strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"{safe_session}_{safe_ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(escalation.model_dump(mode="json"), f, ensure_ascii=False, indent=2)


def invoke_escalation(state: GraphState) -> EscalationOutput:
    category = _determine_category(state)
    attempted_resolution = _build_attempted_resolution(state)
    summary = _generate_summary(state, category, attempted_resolution)
    return EscalationOutput(
        summary=summary,
        category=category,
        customer_message=state["user_message"],
        attempted_resolution=attempted_resolution,
        full_context=_build_full_context(state),
        timestamp=datetime.now(),
        session_id=state["session_id"],
    )


def escalation_node(state: GraphState) -> dict:
    escalation = invoke_escalation(state)

    _save_to_file(escalation)

    # Best-effort Slack publish; file is the authoritative audit trail
    try:
        from tools.slack_publisher import post_to_expert_channel  # lazy import avoids circular import at module level
        post_to_expert_channel(escalation)
    except Exception:
        pass

    plan = state.get("plan")
    language = plan.language if plan else "uk"
    return {
        "final_response": get_escalation_message(language),
        "escalated": True,
    }
