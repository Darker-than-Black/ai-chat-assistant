"""Inter-agent Pydantic contracts. All graph nodes communicate via these models — never free text."""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict


class Source(BaseModel):
    title: str
    url: str | None = None
    doc_id: str
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_doc_id(cls, data):
        if isinstance(data, dict) and not data.get("doc_id"):
            fallback = data.get("url") or data.get("title")
            if fallback:
                data = {**data, "doc_id": fallback}
        return data


class WorkerResponse(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    found: bool
    answer: str | None = None
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False
    needs_human_reason: str | None = None


class SubTask(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    query: str
    rationale: str


class ResearchPlan(BaseModel):
    is_on_topic: bool
    off_topic_reason: str | None = None
    language: Literal["uk", "en"] = "uk"
    original_query: str
    subtasks: list[SubTask] = Field(default_factory=list)
    needs_human: bool = False
    escalation_reason: str | None = None

    @model_validator(mode="after")
    def validate_consistency(self) -> "ResearchPlan":
        if not self.is_on_topic and self.subtasks:
            raise ValueError("off-topic plan must have empty subtasks")
        if self.needs_human and not self.escalation_reason:
            raise ValueError("needs_human=True requires escalation_reason")
        if self.is_on_topic and not self.needs_human and not self.subtasks:
            raise ValueError("on-topic plan must have at least one subtask")
        return self


class RevisionRequest(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    request: str
    severity: Literal["minor", "major"]


class CritiqueResult(BaseModel):
    verdict: Literal["approve", "revise"]
    freshness_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    structure_score: float = Field(ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)
    revision_requests: list[RevisionRequest] = Field(default_factory=list)
    summary: str = ""

    @model_validator(mode="after")
    def validate_revisions(self) -> "CritiqueResult":
        if self.verdict == "revise" and not self.revision_requests:
            raise ValueError("revise verdict requires at least one revision_request")
        return self


class EscalationOutput(BaseModel):
    summary: str
    category: Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]
    customer_message: str
    attempted_resolution: str
    full_context: dict
    timestamp: datetime
    session_id: str


class GraphState(TypedDict):
    user_message: str
    session_id: str
    user_id: str
    plan: ResearchPlan | None
    worker_responses: Annotated[list[WorkerResponse], operator.add]
    critic_history: list[CritiqueResult]
    retry_count: int
    aggregated_response: str | None
    escalated: bool
    final_response: str | None
