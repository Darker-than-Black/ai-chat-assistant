from language import get_no_answer_message, get_section_label


def test_get_section_label_returns_ukrainian_label() -> None:
    assert get_section_label("legal", "uk") == "Юридична консультація"
    assert (
        get_section_label("procurement_general", "uk")
        == "Загальна інформація про закупівлі"
    )
    assert get_section_label("technical_system", "uk") == "Технічна підтримка"


def test_get_section_label_returns_english_label() -> None:
    assert get_section_label("legal", "en") == "Legal Advice"
    assert get_section_label("procurement_general", "en") == "General Procurement Info"
    assert get_section_label("technical_system", "en") == "Technical Support"


def test_language_helpers_fallback_to_defaults() -> None:
    assert get_section_label("unknown_topic", "uk") == "unknown_topic"
    assert get_no_answer_message("uk") == "Відповідь не знайдена в базі знань."
    assert get_no_answer_message("en") == "No answer found in the knowledge base."
    assert get_no_answer_message("de") == "Відповідь не знайдена в базі знань."
