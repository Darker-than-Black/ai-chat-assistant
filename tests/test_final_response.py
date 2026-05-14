from final_response import aggregate
from schemas import Source, WorkerResponse


def test_aggregate_renders_single_section_with_sources() -> None:
    response = WorkerResponse(
        topic="legal",
        found=True,
        answer="Зміна істотних умов договору допускається лише у визначених випадках.",
        sources=[
            Source(
                title="Закон 922, стаття 41",
                doc_id="law-922-41",
                url="https://zakon.rada.gov.ua/laws/show/922-19#Text",
            )
        ],
        confidence=0.95,
    )

    result = aggregate([response], "uk")

    assert "## Юридична консультація" in result
    assert "Зміна істотних умов договору" in result
    assert "**Джерела:**" in result
    assert "Закон 922, стаття 41" in result


def test_aggregate_renders_multiple_sections_in_fixed_order() -> None:
    responses = [
        WorkerResponse(
            topic="technical_system",
            found=True,
            answer="Перевірте формат файлу та чинність КЕП.",
            confidence=0.82,
        ),
        WorkerResponse(
            topic="procurement_general",
            found=True,
            answer="Відкриті торги включають оголошення, подання пропозицій і оцінку.",
            confidence=0.88,
        ),
    ]

    result = aggregate(responses, "uk")

    # Should be sorted: procurement_general before technical_system
    assert "## Загальна інформація про закупівлі" in result
    assert "## Технічна підтримка" in result
    assert result.index("## Загальна інформація про закупівлі") < result.index("## Технічна підтримка")
    assert "\n\n---\n\n" in result


def test_aggregate_deduplicates_by_keeping_latest() -> None:
    responses = [
        WorkerResponse(
            topic="legal",
            found=True,
            answer="Перша версія відповіді.",
            confidence=0.8,
        ),
        WorkerResponse(
            topic="legal",
            found=True,
            answer="Друга версія відповіді (оновлена).",
            confidence=0.9,
        ),
    ]

    result = aggregate(responses, "uk")

    assert "## Юридична консультація" in result
    assert "Друга версія відповіді (оновлена)." in result
    assert "Перша версія відповіді." not in result


def test_aggregate_skips_not_found_sections() -> None:
    responses = [
        WorkerResponse(
            topic="legal",
            found=False,
            answer=None,
            confidence=0.2,
        ),
        WorkerResponse(
            topic="technical_system",
            found=True,
            answer="Спробуйте повторити вхід після перевірки КЕП.",
            confidence=0.78,
        ),
    ]

    result = aggregate(responses, "uk")

    assert "## Юридична консультація" not in result
    assert "## Технічна підтримка" in result


def test_aggregate_returns_no_answer_message_when_all_sections_empty() -> None:
    responses = [
        WorkerResponse(
            topic="legal",
            found=False,
            answer=None,
            confidence=0.1,
        )
    ]

    assert aggregate(responses, "en") == "No answer found in the knowledge base."


def test_aggregate_uses_english_section_labels() -> None:
    response = WorkerResponse(
        topic="technical_system",
        found=True,
        answer="Check the file format and your signature token.",
        confidence=0.84,
    )

    result = aggregate([response], "en")

    assert "## Technical Support" in result
