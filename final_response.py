"""Format worker responses into the final user-facing markdown document."""

from __future__ import annotations

from language import get_no_answer_message, get_section_label
from schemas import WorkerResponse


def aggregate(responses: list[WorkerResponse], language: str = "uk") -> str:
    best: dict[str, WorkerResponse] = {}
    for resp in responses:
        existing = best.get(resp.topic)
        if existing is None:
            best[resp.topic] = resp
        elif resp.found and (not existing.found or resp.confidence > existing.confidence):
            best[resp.topic] = resp

    topic_order = ["legal", "procurement_general", "technical_system"]
    ordered = [best[t] for t in topic_order if t in best]

    sections: list[str] = []

    for response in ordered:
        if not response.found:
            continue

        section_parts = [f"## {get_section_label(response.topic, language)}"]

        if response.answer:
            section_parts.append(response.answer)

        if response.sources:
            source_lines = ["**Джерела:**"]
            for source in response.sources:
                source_line = f"- {source.title}"
                if source.url:
                    source_line += f" — {source.url}"
                source_lines.append(source_line)
            section_parts.append("\n".join(source_lines))

        sections.append("\n\n".join(section_parts))

    if not sections:
        return get_no_answer_message(language)

    return "\n\n---\n\n".join(sections)
