import pytest
from pydantic import ValidationError

from schemas import (
    CritiqueResult,
    ResearchPlan,
    RevisionRequest,
    Source,
    SubTask,
    WorkerResponse,
)


def _subtask() -> SubTask:
    return SubTask(topic="legal", query="test", rationale="test")


class TestWorkerResponse:
    def test_valid_confidence_bounds(self) -> None:
        for v in (0.0, 0.5, 1.0):
            r = WorkerResponse(topic="legal", found=True, confidence=v)
            assert r.confidence == v

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            WorkerResponse(topic="legal", found=True, confidence=1.1)

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            WorkerResponse(topic="legal", found=True, confidence=-0.1)


class TestResearchPlan:
    def test_off_topic_with_subtasks_raises(self) -> None:
        with pytest.raises(ValidationError, match="off-topic"):
            ResearchPlan(
                is_on_topic=False,
                original_query="test",
                subtasks=[_subtask()],
            )

    def test_needs_human_missing_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="escalation_reason"):
            ResearchPlan(
                is_on_topic=True,
                original_query="test",
                needs_human=True,
                subtasks=[_subtask()],
            )

    def test_on_topic_empty_subtasks_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one subtask"):
            ResearchPlan(is_on_topic=True, original_query="test", subtasks=[])

    def test_valid_off_topic(self) -> None:
        plan = ResearchPlan(
            is_on_topic=False,
            off_topic_reason="Not procurement",
            original_query="test",
        )
        assert not plan.is_on_topic
        assert plan.subtasks == []

    def test_valid_on_topic(self) -> None:
        plan = ResearchPlan(
            is_on_topic=True,
            original_query="test",
            subtasks=[_subtask()],
        )
        assert plan.subtasks

    def test_valid_needs_human(self) -> None:
        plan = ResearchPlan(
            is_on_topic=True,
            original_query="test",
            needs_human=True,
            escalation_reason="Needs specialist",
        )
        assert plan.needs_human


class TestSource:
    def test_url_is_optional(self) -> None:
        src = Source(title="Закон 922", doc_id="law-922")
        assert src.url is None

    def test_with_url(self) -> None:
        src = Source(title="Закон 922", doc_id="law-922", url="https://example.com")
        assert src.url == "https://example.com"

    def test_metadata_defaults_to_empty_dict(self) -> None:
        src = Source(title="Закон 922", doc_id="law-922")
        assert src.metadata == {}

    def test_metadata_accepts_arbitrary_dict(self) -> None:
        src = Source(
            title="Закон 922",
            doc_id="law-922",
            metadata={"version_date": "23.04.2026", "article_number": "17"},
        )
        assert src.metadata["version_date"] == "23.04.2026"
        assert src.metadata["article_number"] == "17"

    def test_doc_id_is_inferred_from_url_when_missing(self) -> None:
        src = Source(
            title="Prozorro",
            url="https://prozorro.gov.ua",
        )
        assert src.doc_id == "https://prozorro.gov.ua"

    def test_doc_id_is_inferred_from_title_when_missing(self) -> None:
        src = Source(title="Закон 922")
        assert src.doc_id == "Закон 922"

    def test_worker_response_accepts_sources_without_doc_id(self) -> None:
        response = WorkerResponse(
            topic="procurement_general",
            found=True,
            answer="Переговорна процедура застосовується у виняткових випадках.",
            sources=[
                {
                    "title": "Закон України «Про публічні закупівлі»",
                    "url": "https://zakon.rada.gov.ua/laws/show/922-19",
                },
                {
                    "title": "Prozorro",
                    "url": "https://prozorro.gov.ua",
                },
            ],
            confidence=0.9,
        )

        assert response.sources[0].doc_id == "https://zakon.rada.gov.ua/laws/show/922-19"
        assert response.sources[1].doc_id == "https://prozorro.gov.ua"


class TestRevisionRequest:
    def test_valid_revision_request(self) -> None:
        rr = RevisionRequest(
            topic="legal",
            request="Уточни джерело норми.",
            severity="major",
        )
        assert rr.topic == "legal"
        assert rr.severity == "major"

    def test_invalid_topic_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RevisionRequest(topic="other", request="x", severity="minor")

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RevisionRequest(topic="legal", request="x", severity="critical")


class TestCritiqueResult:
    def _scores(self) -> dict:
        return {
            "freshness_score": 0.9,
            "completeness_score": 0.9,
            "structure_score": 0.9,
        }

    def test_valid_approve(self) -> None:
        cr = CritiqueResult(verdict="approve", **self._scores())
        assert cr.verdict == "approve"
        assert cr.revision_requests == []

    def test_valid_revise_with_request(self) -> None:
        cr = CritiqueResult(
            verdict="revise",
            **self._scores(),
            revision_requests=[
                RevisionRequest(topic="legal", request="x", severity="minor")
            ],
        )
        assert cr.verdict == "revise"
        assert len(cr.revision_requests) == 1

    def test_revise_without_revision_requests_raises(self) -> None:
        with pytest.raises(ValidationError, match="revise verdict requires"):
            CritiqueResult(verdict="revise", **self._scores())

    def test_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            CritiqueResult(
                verdict="approve",
                freshness_score=1.1,
                completeness_score=0.5,
                structure_score=0.5,
            )

    def test_negative_score_raises(self) -> None:
        with pytest.raises(ValidationError):
            CritiqueResult(
                verdict="approve",
                freshness_score=-0.1,
                completeness_score=0.5,
                structure_score=0.5,
            )

    def test_escalate_verdict_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CritiqueResult(verdict="escalate", **self._scores())
