"""End-to-end tests over the golden dataset.

Two layers:
  1. Golden-dataset structure validation (always runs).
  2. Full graph invocation + DeepEval Correctness/Answer-Relevancy metrics
     (marked @pytest.mark.eval; skipped without API access).

Results from the eval layer are appended to ``tests/results/e2e_baseline_<ts>.json``
so we can track Correctness / Answer Relevancy over time.

Run only the structural checks: ``pytest tests/test_e2e.py``
Run the full eval suite:        ``pytest -m eval tests/test_e2e.py``
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from schemas import GraphState

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"
ALLOWED_TOPICS = {"legal", "procurement_general", "technical_system"}
ALLOWED_CATEGORIES = {"happy_path", "edge_case", "off_topic", "escalation"}


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _load_dataset() -> list[dict[str, Any]]:
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _has_eval_credentials() -> bool:
    """The eval layer needs a real LLM. Skip cleanly when keys are missing."""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def _initial_state(entry: dict[str, Any]) -> GraphState:
    return {
        "user_message": entry["input"],
        "session_id": f"test:{entry['id']}",
        "user_id": "test-user",
        "plan": None,
        "worker_responses": [],
        "critic_history": [],
        "retry_count": 0,
        "aggregated_response": None,
        "escalated": False,
        "final_response": None,
    }


# ─────────────────────────────────────────────────────────────────
# 1. Golden dataset — structural validation (always runs)
# ─────────────────────────────────────────────────────────────────

def test_golden_dataset_loads() -> None:
    dataset = _load_dataset()
    assert isinstance(dataset, list)
    assert 15 <= len(dataset) <= 25, "golden dataset should hold 15–25 cases"


def test_golden_dataset_categories_balanced() -> None:
    """At least 3 examples in each of happy / edge / failure-style buckets."""
    dataset = _load_dataset()
    happy = [e for e in dataset if e["category"] == "happy_path"]
    edge = [e for e in dataset if e["category"] == "edge_case"]
    failure = [e for e in dataset if e["category"] in {"off_topic", "escalation"}]

    assert len(happy) >= 3
    assert len(edge) >= 3
    assert len(failure) >= 3


@pytest.mark.parametrize("entry", _load_dataset(), ids=lambda e: e["id"])
def test_golden_dataset_entry_schema(entry: dict[str, Any]) -> None:
    """Every dataset entry must follow the ARCHITECTURE § 13.2 contract."""
    required = {
        "id",
        "category",
        "input",
        "language",
        "expected_topics",
        "expected_output",
        "expected_sources_doc_ids",
        "should_escalate",
    }
    assert required <= set(entry.keys()), f"missing keys in {entry.get('id')}"

    assert entry["category"] in ALLOWED_CATEGORIES
    assert entry["language"] in {"uk", "en"}
    assert isinstance(entry["input"], str) and entry["input"].strip()
    assert isinstance(entry["expected_output"], str)
    assert isinstance(entry["expected_topics"], list)
    assert all(t in ALLOWED_TOPICS for t in entry["expected_topics"])
    assert isinstance(entry["expected_sources_doc_ids"], list)
    assert isinstance(entry["should_escalate"], bool)


def test_golden_dataset_ids_unique() -> None:
    dataset = _load_dataset()
    ids = [e["id"] for e in dataset]
    assert len(ids) == len(set(ids)), "duplicate id in golden dataset"


def test_off_topic_entries_have_no_expected_topics() -> None:
    """Off-topic queries should not name any in-scope topic — defense in depth."""
    for entry in _load_dataset():
        if entry["category"] == "off_topic":
            assert entry["expected_topics"] == [], entry["id"]
            assert entry["should_escalate"] is False, entry["id"]


def test_escalation_entries_marked_for_escalation() -> None:
    for entry in _load_dataset():
        if entry["category"] == "escalation":
            assert entry["should_escalate"] is True, entry["id"]


# ─────────────────────────────────────────────────────────────────
# 2. End-to-end LLM eval — needs API access
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
@pytest.mark.skipif(not _has_eval_credentials(), reason="LLM API key not configured")
@pytest.mark.parametrize("entry", _load_dataset(), ids=lambda e: e["id"])
def test_e2e_graph_runs_golden_case(entry: dict[str, Any]) -> None:
    """Run each golden case through the full graph and score it.

    Asserts behavioral outcomes (escalation flag, topic coverage) and
    appends Correctness / Answer-Relevancy scores to a baseline file
    so successive runs can be compared.
    """
    from deepeval import evaluate
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase, SingleTurnParams

    from supervisor import build_graph

    graph = build_graph()
    state = _initial_state(entry)
    config = {"configurable": {"thread_id": state["session_id"]}}

    final_state = graph.invoke(state, config=config)

    escalated = bool(final_state.get("escalated"))
    plan = final_state.get("plan")
    refused_off_topic = plan is not None and not plan.is_on_topic

    # Hard contract: cases marked should_escalate must NOT receive a normal worker
    # answer. Either the escalation path or the off-topic refusal path satisfies
    # this — both decline gracefully, which is the user-visible contract.
    # Over-escalation on happy/edge paths (Critic exhausting retries) is a
    # quality regression we track in the baseline, not a hard failure, since
    # critic strictness varies with RAG content quality.
    if entry["should_escalate"]:
        assert escalated or refused_off_topic, (
            f"{entry['id']}: must-escalate case answered normally "
            f"(escalated={escalated}, on_topic={plan.is_on_topic if plan else None})"
        )

    # Topic coverage applies only when the planner produced subtasks. Direct
    # escalation (needs_human=true) and off-topic refusal both legitimately
    # leave subtasks empty — see ResearchPlan validator in schemas.py.
    if entry["expected_topics"] and plan is not None and plan.subtasks:
        produced = {st.topic for st in plan.subtasks}
        expected = set(entry["expected_topics"])
        assert produced & expected, (
            f"{entry['id']}: planner missed all expected topics "
            f"(expected={expected}, got={produced})"
        )

    actual_output = final_state.get("final_response") or ""
    correctness = GEval(
        name="Correctness",
        evaluation_steps=[
            "Compare 'actual output' against 'expected output' on factual content.",
            "Reward partial alignment when the same key facts appear in different wording.",
            "Penalise contradictions, missing critical facts, or made-up details.",
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        model="gpt-4o-mini",
        threshold=0.5,
    )
    relevancy = AnswerRelevancyMetric(threshold=0.6, model="gpt-4o-mini")

    test_case = LLMTestCase(
        input=entry["input"],
        actual_output=actual_output,
        expected_output=entry["expected_output"],
    )
    result = evaluate(test_cases=[test_case], metrics=[correctness, relevancy])

    _append_baseline(entry, actual_output, result, escalated=escalated, refused_off_topic=refused_off_topic)


def _append_baseline(
    entry: dict[str, Any],
    actual_output: str,
    result: Any,
    *,
    escalated: bool,
    refused_off_topic: bool,
) -> None:
    """Append a single-case record to ``tests/results/e2e_baseline_<ts>.json``."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"e2e_baseline_{ts}.json"

    record = {
        "id": entry["id"],
        "category": entry["category"],
        "input": entry["input"],
        "actual_output": actual_output,
        "expected_output": entry["expected_output"],
        "expected_escalation": entry["should_escalate"],
        "actual_escalation": escalated,
        "refused_off_topic": refused_off_topic,
        "escalation_match": escalated == entry["should_escalate"],
        "metrics": _extract_metric_scores(result),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing.append(record)
        payload = existing
    else:
        payload = [record]

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_metric_scores(result: Any) -> dict[str, float | None]:
    """Pull (metric_name → score) from a DeepEval EvaluationResult."""
    scores: dict[str, float | None] = {}
    test_results = getattr(result, "test_results", None) or []
    for tr in test_results:
        for m in getattr(tr, "metrics_data", []) or []:
            scores[getattr(m, "name", "unknown")] = getattr(m, "score", None)
    return scores
