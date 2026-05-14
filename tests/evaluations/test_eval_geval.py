"""LLM-as-a-Judge evaluators for the Prozorro support assistant.

Covers all evaluation dimensions from ARCHITECTURE.md § 13.3:
  - Groundedness      (Lawyer, Common Support, Technical Support)
  - Plan Quality      (Planner)
  - Off-topic         Adherence (Planner refusal)
  - Critique Quality  (Critic)
  - Answer Relevancy  (final response)
  - Source Citation Quality (final response)
  - Tool Correctness  (Lawyer, Technical Support)

Run selectively:  pytest -m eval tests/evaluations/
Run all evals:    deepeval test run tests/evaluations/
"""
import json

import pytest
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall, ToolCallParams


# ─────────────────────────────────────────────────────────────────
# Shared metric factory
# ─────────────────────────────────────────────────────────────────

def _groundedness_metric(threshold: float = 0.7) -> GEval:
    return GEval(
        name="Groundedness",
        evaluation_steps=[
            "Extract every factual claim from 'actual output'.",
            "For each claim, check whether it is directly supported by text in 'retrieval context'.",
            "Claims absent from retrieval context count as ungrounded even if generally true.",
            "Score = grounded claims / total claims.",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.RETRIEVAL_CONTEXT],
        model="gpt-4o-mini",
        threshold=threshold,
    )


# ─────────────────────────────────────────────────────────────────
# 1. Groundedness — Lawyer Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_lawyer_groundedness():
    """Lawyer answer is grounded in retrieved legal text (laws collection)."""
    test_case = LLMTestCase(
        input="Який штраф за порушення за статтею 164-14?",
        actual_output=(
            "За статтею 164-14 КУпАП штраф для посадових осіб становить "
            "від 1500 до 3000 неоподатковуваних мінімумів доходів громадян."
        ),
        retrieval_context=[
            "Стаття 164-14 КУпАП встановлює адміністративну відповідальність "
            "за порушення законодавства про закупівлі. Штраф становить від 1500 "
            "до 3000 неоподатковуваних мінімумів доходів громадян для посадових осіб."
        ],
    )
    evaluate(test_cases=[test_case], metrics=[_groundedness_metric()])


# ─────────────────────────────────────────────────────────────────
# 2. Groundedness — Common Support Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_common_support_groundedness():
    """Common Support answer is grounded in retrieved articles."""
    test_case = LLMTestCase(
        input="Як подати тендерну пропозицію в ЕСЗ?",
        actual_output=(
            "Для подання тендерної пропозиції учасник завантажує пакет документів "
            "через особистий кабінет в ЕСЗ, підписує їх кваліфікованим електронним "
            "підписом (КЕП) та натискає кнопку «Подати пропозицію». Строк подання — "
            "до дати закінчення прийому пропозицій, зазначеної в оголошенні."
        ),
        retrieval_context=[
            "Учасник завантажує документи через електронну систему закупівель (ЕСЗ), "
            "підписує їх кваліфікованим електронним підписом (КЕП) та подає не пізніше "
            "дати закінчення прийому тендерних пропозицій, вказаної в оголошенні про закупівлю."
        ],
    )
    evaluate(test_cases=[test_case], metrics=[_groundedness_metric()])


# ─────────────────────────────────────────────────────────────────
# 3. Groundedness — Technical Support Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_technical_support_groundedness():
    """Technical Support answer is grounded in retrieved tutorial articles."""
    test_case = LLMTestCase(
        input="Що робити, якщо майданчик повертає помилку при поданні КЕП?",
        actual_output=(
            "Поширені причини помилки КЕП: прострочений сертифікат, файл підпису "
            "у неправильному форматі (потрібен PKCS-7, розширення .p7s), проблеми "
            "з браузерним кешем. Рекомендовані кроки: перевірте термін дії сертифіката, "
            "переконайтесь у форматі .p7s та очистіть кеш браузера."
        ),
        retrieval_context=[
            "Поширені причини помилки КЕП у ЕСЗ: прострочений сертифікат підпису; "
            "неправильний формат файлу підпису — необхідний PKCS-7 (.p7s); "
            "проблеми з кешем браузера. Рекомендовані дії: перевірте термін дії "
            "сертифіката, переконайтесь у форматі .p7s, очистіть кеш браузера і повторіть."
        ],
    )
    evaluate(test_cases=[test_case], metrics=[_groundedness_metric()])


# ─────────────────────────────────────────────────────────────────
# 4. Plan Quality — Planner Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_planner_plan_quality():
    """Planner ResearchPlan correctly identifies all topics and creates specific subtasks."""
    plan = {
        "is_on_topic": True,
        "language": "uk",
        "original_query": "Яка комісія майданчику Prozorro і чи порушує це статтю 15 Закону 922?",
        "subtasks": [
            {
                "topic": "technical_system",
                "query": "Розмір комісії електронного майданчика Prozorro",
                "rationale": "Технічне питання про умови роботи та вартість послуг майданчика.",
            },
            {
                "topic": "legal",
                "query": "Стаття 15 Закону 922 щодо комісій та оплати за участь у закупівлях",
                "rationale": "Правова перевірка відповідності розміру комісії вимогам законодавства.",
            },
        ],
        "needs_human": False,
    }
    plan_quality = GEval(
        name="Plan Quality",
        evaluation_steps=[
            "Verify 'actual output' is a JSON plan with 'is_on_topic' set to true and a non-empty 'subtasks' list.",
            "Check that the plan identifies both topics present in the query: "
            "'technical_system' (platform fee question) and 'legal' (Law 922 compliance).",
            "Each subtask must map directly to a distinct part of the user question with a specific, actionable query.",
            "Deduct for missing topics, duplicate subtasks, or vague queries like 'знайди інформацію'.",
            "Score 1.0 for complete topic coverage with specific subtasks; 0.0 for missing a major topic.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model="gpt-4o-mini",
        threshold=0.7,
    )
    test_case = LLMTestCase(
        input="Яка комісія майданчику Prozorro і чи порушує це статтю 15 Закону 922?",
        actual_output=json.dumps(plan, ensure_ascii=False),
    )
    evaluate(test_cases=[test_case], metrics=[plan_quality])


# ─────────────────────────────────────────────────────────────────
# 5. Off-topic Adherence — Planner refusal response
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_planner_off_topic_adherence():
    """Off-topic refusal politely declines and explains the system's actual scope."""
    refusal_message = (
        "Ваш запит виходить за межі нашої компетенції. "
        "Асистент надає підтримку виключно з питань публічних закупівель України: "
        "роботи в системі Prozorro, тендерних процедур та законодавства про закупівлі. "
        "Будь ласка, сформулюйте питання в межах цих тем."
    )
    off_topic_adherence = GEval(
        name="Off-topic Adherence",
        evaluation_steps=[
            "Confirm 'actual output' declines to answer the user's off-topic query.",
            "Verify the response describes the system's actual scope "
            "(Ukrainian public procurement, Prozorro, tender law).",
            "Check the tone is polite and constructive, not dismissive.",
            "Verify the response does NOT partially attempt to answer the off-topic question.",
            "Score 1.0 for a clear, scoped, polite refusal; deduct for answering off-topic content or rude tone.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model="gpt-4o-mini",
        threshold=0.8,
    )
    test_case = LLMTestCase(
        input="Який холодильник краще купити для дому?",
        actual_output=refusal_message,
    )
    evaluate(test_cases=[test_case], metrics=[off_topic_adherence])


# ─────────────────────────────────────────────────────────────────
# 6. Critique Quality — Critic Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_critic_verdict_quality():
    """Critic 'revise' verdict is justified and contains specific, actionable revision requests."""
    worker_summary = (
        "Юридичний агент відповів: «Відповідно до Закону 922 закупівля є правомірною.» "
        "Джерело: Закон 922 станом на 2020 рік. "
        "Питання стосувалось актуальності норм з урахуванням змін 2024 року."
    )
    critique = {
        "verdict": "revise",
        "freshness_score": 0.3,
        "completeness_score": 0.6,
        "structure_score": 0.8,
        "gaps": [
            "Відповідь посилається на редакцію Закону 922 від 2020 року, "
            "тоді як у 2024 році внесено суттєві зміни щодо прозорості закупівель."
        ],
        "revision_requests": [
            {
                "topic": "legal",
                "request": (
                    "Оновіть відповідь з урахуванням змін до Закону 922, "
                    "прийнятих у 2024 році, зокрема поправок щодо електронного "
                    "документообігу та прозорості."
                ),
                "severity": "major",
            }
        ],
        "summary": "Юридична частина застаріла, потребує оновлення джерел до актуальної редакції.",
    }
    critique_quality = GEval(
        name="Critique Quality",
        evaluation_steps=[
            "Verify 'actual output' is a JSON critique with 'verdict': 'revise' and non-empty 'revision_requests'.",
            "Check the revise verdict is justified: input says source is from 2020 but 2024 changes apply.",
            "Verify revision_requests name the exact problem (outdated law version) and specify what to do "
            "(update to 2024 amendments).",
            "Check freshness_score ≤ 0.4, reflecting the outdated source.",
            "Score 1.0 for a well-justified, specific critique; deduct for vague or unjustified requests.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model="gpt-4o-mini",
        threshold=0.7,
    )
    test_case = LLMTestCase(
        input=worker_summary,
        actual_output=json.dumps(critique, ensure_ascii=False),
    )
    evaluate(test_cases=[test_case], metrics=[critique_quality])


# ─────────────────────────────────────────────────────────────────
# 7. Answer Relevancy — final aggregated response
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_answer_relevancy():
    """Final aggregated response is relevant to the user's procurement question."""
    relevancy = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o-mini")
    test_case = LLMTestCase(
        input="Як учаснику подати скаргу на дії замовника до АМКУ?",
        actual_output=(
            "**Правова підстава**\n"
            "Відповідно до статті 18 Закону України «Про публічні закупівлі» (Закон 922), "
            "учасник має право подати скаргу до Антимонопольного комітету України (АМКУ). "
            "Строк — 10 робочих днів з дня, коли учасник дізнався або мав дізнатися про порушення.\n\n"
            "**Порядок подання через ЕСЗ**\n"
            "Увійдіть до кабінету учасника → розділ «Скарги» → «Нова скарга» → "
            "заповніть форму, додайте підтверджуючі документи → підпишіть КЕП і надішліть.\n\n"
            "Джерела: Закон 922 ст. 18; Регламент АМКУ щодо розгляду скарг."
        ),
    )
    evaluate(test_cases=[test_case], metrics=[relevancy])


# ─────────────────────────────────────────────────────────────────
# 8. Source Citation Quality — final response cites specific sources
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_source_citation_quality():
    """Final response references specific laws, article numbers, or document titles."""
    citation_quality = GEval(
        name="Source Citation Quality",
        evaluation_steps=[
            "Identify all citations in 'actual output': law names, article numbers, URLs, document titles.",
            "Verify at least one specific citation is present "
            "(e.g. 'Закон 922 ст. 18', 'КМУ постанова 1178', a prozorro.gov.ua URL).",
            "Generic phrases like 'за законодавством' or 'відповідно до норм' are NOT specific citations.",
            "Citations must be plausibly relevant to the question and the answer content.",
            "Score 1.0 for two or more specific citations; 0.6 for one specific citation; "
            "0.0 for only generic references or none at all.",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        model="gpt-4o-mini",
        threshold=0.6,
    )
    test_case = LLMTestCase(
        input="Як учаснику подати скаргу до АМКУ?",
        actual_output=(
            "Скарга до АМКУ подається протягом 10 робочих днів відповідно до статті 18 "
            "Закону України «Про публічні закупівлі» (Закон 922). "
            "Форму скарги та порядок її подання затверджено Регламентом АМКУ "
            "(наказ від 2020 року)."
        ),
    )
    evaluate(test_cases=[test_case], metrics=[citation_quality])


# ─────────────────────────────────────────────────────────────────
# 9. Tool Correctness — Lawyer Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_lawyer_tool_correctness():
    """Lawyer calls rag_search with collection='laws' — never web_search or articles."""
    tool_correctness = ToolCorrectnessMetric(
        threshold=0.9,
        evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
        model="gpt-4o-mini",
    )
    rag_call = ToolCall(
        name="rag_search",
        input_parameters={
            "query": "стаття 164-14 адміністративна відповідальність закупівлі",
            "collection": "laws",
        },
        output=(
            "Стаття 164-14 КУпАП: штраф від 1500 до 3000 неоподатковуваних "
            "мінімумів доходів громадян для посадових осіб."
        ),
    )
    test_case = LLMTestCase(
        input="Який штраф передбачає стаття 164-14 за порушення законодавства про закупівлі?",
        actual_output=(
            "Стаття 164-14 КУпАП передбачає штраф від 1500 до 3000 неоподатковуваних "
            "мінімумів доходів громадян для посадових осіб."
        ),
        tools_called=[rag_call],
        expected_tools=[rag_call],
    )
    evaluate(test_cases=[test_case], metrics=[tool_correctness])


# ─────────────────────────────────────────────────────────────────
# 10. Tool Correctness — Technical Support Agent
# ─────────────────────────────────────────────────────────────────

@pytest.mark.eval
def test_technical_support_tool_correctness():
    """Technical Support uses rag_search_articles, github_repo_search for library queries."""
    tool_correctness = ToolCorrectnessMetric(
        threshold=0.7,
        model="gpt-4o-mini",
    )
    tools_called = [
        ToolCall(
            name="rag_search_articles",
            input_parameters={"query": "prozorro-eds бібліотека методи TypeScript"},
            output="Статті про prozorro-eds: методи ініціалізації та підпису документів...",
        ),
        ToolCall(
            name="github_repo_search",
            input_parameters={"query": "prozorro-eds public methods API"},
            output=(
                "---\nРепозиторій: ProzorroUKR/prozorro-eds\nФайл: README.md\n"
                "ProzorroEds.init() — initialize the library\n"
                "Джерело: https://github.com/ProzorroUKR/prozorro-eds/blob/master/README.md"
            ),
        ),
    ]
    expected_tools = [
        ToolCall(
            name="rag_search_articles",
            input_parameters={"query": "prozorro-eds бібліотека методи TypeScript"},
            output="Статті про prozorro-eds...",
        ),
        ToolCall(
            name="github_repo_search",
            input_parameters={"query": "prozorro-eds public methods API"},
            output="README.md, ProzorroEds.init()...",
        ),
    ]
    test_case = LLMTestCase(
        input="Які публічні методи має бібліотека prozorro-eds?",
        actual_output=(
            "Бібліотека prozorro-eds надає такі публічні методи: "
            "ProzorroEds.init() — ініціалізація, ProzorroEds.sign() — підписання документів, "
            "ProzorroEds.verify() — верифікація підпису."
        ),
        tools_called=tools_called,
        expected_tools=expected_tools,
    )
    evaluate(test_cases=[test_case], metrics=[tool_correctness])
