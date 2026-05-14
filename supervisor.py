"""Phase 3 supervisor graph: planner → fan-out → workers → aggregator → critic loop."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

# Retry policy for all LLM-calling nodes.
# OpenAI TPM rate-limit windows are 60 s; exhausting 200 k TPM means up to
# ~60 s of backoff is needed. With initial_interval=2 + backoff_factor=2:
#   attempt 2: ~2–3 s, attempt 3: ~4–7 s, attempt 4: ~8–15 s, attempt 5: ~16–30 s
# Total wait before giving up: ~30–55 s, enough for the oldest requests to roll
# out of the window. default_retry_on returns True for openai.RateLimitError.
_LLM_RETRY = RetryPolicy(
    initial_interval=2.0,
    backoff_factor=2.0,
    max_interval=30.0,
    max_attempts=5,
    jitter=True,
)

from agents.common_support import common_support_node
from agents.critic import critic_node
from agents.escalation import escalation_node
from agents.lawyer import lawyer_node
from agents.planner import invoke_planner
from agents.technical_support import technical_support_node
from config import settings
from final_response import aggregate
from schemas import GraphState, WorkerResponse

_TOPIC_NODE = {
    "legal": "lawyer_node",
    "procurement_general": "common_support_node",
    "technical_system": "technical_support_node",
}


def planner_node(state: GraphState) -> dict:
    return {"plan": invoke_planner(state["user_message"])}


def fan_out_dispatcher(state: GraphState) -> dict:
    return {}


def fan_out_send(state: GraphState) -> list[Send]:
    return [
        Send(_TOPIC_NODE[st.topic], {"subtask": st, "revision_feedback": None})
        for st in state["plan"].subtasks
    ]


def aggregate_responses_node(state: GraphState) -> dict:
    # Keep the best response per topic: prefer found=True and highest confidence.
    # "Last wins" would let a bad revision response overwrite a good initial one.
    best: dict[str, WorkerResponse] = {}
    for resp in state["worker_responses"]:
        existing = best.get(resp.topic)
        if existing is None:
            best[resp.topic] = resp
        elif resp.found and (not existing.found or resp.confidence > existing.confidence):
            best[resp.topic] = resp

    topic_order = ["legal", "procurement_general", "technical_system"]
    ordered = [best[t] for t in topic_order if t in best]

    sections: list[str] = []
    for resp in ordered:
        if resp.found and resp.answer:
            sections.append(resp.answer)

    aggregated = "\n\n---\n\n".join(sections) if sections else ""
    return {"aggregated_response": aggregated}


def targeted_redispatcher(state: GraphState) -> dict:
    return {}


def targeted_redispatch_send(state: GraphState) -> list[Send]:
    last_critique = state["critic_history"][-1]
    sends: list[Send] = []
    seen_topics: set[str] = set()
    for rev_req in last_critique.revision_requests:
        if rev_req.topic in seen_topics:
            continue
        seen_topics.add(rev_req.topic)
        subtask = next(
            (st for st in state["plan"].subtasks if st.topic == rev_req.topic),
            None,
        )
        if subtask is None:
            continue
        sends.append(
            Send(
                _TOPIC_NODE[rev_req.topic],
                {"subtask": subtask, "revision_feedback": rev_req.request},
            )
        )
    return sends


def off_topic_node(state: GraphState) -> dict:
    reason = state["plan"].off_topic_reason if state.get("plan") else None
    message = "Вибачте, це питання поза межами системи ProZorro."
    if reason:
        message = f"{message} {reason}"
    return {"final_response": message, "escalated": False}


def final_response_node(state: GraphState) -> dict:
    language = state["plan"].language if state.get("plan") else "uk"
    return {
        "final_response": aggregate(
            state.get("worker_responses", []),
            language,
        )
    }


def route_after_planner(state: GraphState) -> str:
    plan = state["plan"]
    if not plan.is_on_topic:
        return "off_topic_node"
    if plan.needs_human:
        return "escalation_node"
    return "fan_out_dispatcher"


def route_after_critic(state: GraphState) -> str:
    last_critique = state["critic_history"][-1]
    if last_critique.verdict == "approve":
        return "final_response_node"
    if state["retry_count"] >= settings.critic_max_retries:
        return "escalation_node"
    # After the first revision, approve if average score meets the minimum threshold.
    # Prevents an overly strict Critic from looping when workers have already provided
    # real content but can't satisfy citation-format requirements the RAG may not supply.
    if state["retry_count"] >= 1:
        avg = (
            last_critique.freshness_score
            + last_critique.completeness_score
            + last_critique.structure_score
        ) / 3
        if avg >= settings.critic_min_approve_score:
            return "final_response_node"
    return "targeted_redispatcher"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    builder = StateGraph(GraphState)
    builder.add_node("planner_node", planner_node, retry_policy=_LLM_RETRY)
    builder.add_node("fan_out_dispatcher", fan_out_dispatcher)
    builder.add_node("lawyer_node", lawyer_node, retry_policy=_LLM_RETRY)
    builder.add_node("common_support_node", common_support_node, retry_policy=_LLM_RETRY)
    builder.add_node("technical_support_node", technical_support_node, retry_policy=_LLM_RETRY)
    builder.add_node("aggregate_responses_node", aggregate_responses_node)
    builder.add_node("critic_node", critic_node, retry_policy=_LLM_RETRY)
    builder.add_node("targeted_redispatcher", targeted_redispatcher)
    builder.add_node("off_topic_node", off_topic_node)
    builder.add_node("escalation_node", escalation_node)
    builder.add_node("final_response_node", final_response_node)

    builder.add_edge(START, "planner_node")
    builder.add_conditional_edges(
        "planner_node",
        route_after_planner,
        {
            "fan_out_dispatcher": "fan_out_dispatcher",
            "off_topic_node": "off_topic_node",
            "escalation_node": "escalation_node",
        },
    )
    builder.add_conditional_edges(
        "fan_out_dispatcher",
        fan_out_send,
        ["lawyer_node", "common_support_node", "technical_support_node"],
    )
    for worker in ("lawyer_node", "common_support_node", "technical_support_node"):
        builder.add_edge(worker, "aggregate_responses_node")
    builder.add_edge("aggregate_responses_node", "critic_node")
    builder.add_conditional_edges(
        "critic_node",
        route_after_critic,
        {
            "final_response_node": "final_response_node",
            "escalation_node": "escalation_node",
            "targeted_redispatcher": "targeted_redispatcher",
        },
    )
    builder.add_conditional_edges(
        "targeted_redispatcher",
        targeted_redispatch_send,
        ["lawyer_node", "common_support_node", "technical_support_node"],
    )
    builder.add_edge("off_topic_node", END)
    builder.add_edge("escalation_node", END)
    builder.add_edge("final_response_node", END)
    if checkpointer is None:
        checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
