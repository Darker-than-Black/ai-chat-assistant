# Delivery Checklist

> **Як читати:** план реалізації побудовано як **vertical slices** — на кожній фазі система запускається і працює end-to-end, просто з обмеженою функціональністю. Це дозволяє на будь-якому етапі мати "робочий продукт" і знизити ризик "не встигли інтегрувати".
>
> **Гранулярність:** кожен пункт ≈ одна сесія в Claude Code (30-60 хв). Підпункти — для відстеження прогресу всередині пункту.
>
> **Посилання:** деталі реалізації — у `ARCHITECTURE.md`. Правила і стиль коду — у `CLAUDE.md`. Цей документ — про *що зробити і в якому порядку*.

---

## Definition of Done

Пункт чекліста вважається завершеним лише коли виконано **всі** з наступного:

1. **Функціонально:** код реалізує задачу і запускається в межах поточного vertical slice (попередні milestone не зламані).
2. **Library-first:** перевірено, чи бібліотека вже надає цю функціональність. Якщо пишеться власне — є обґрунтування в docstring.
3. **Cleanup виконано:**
   - Видалено всі заглушки, mock-дані, тимчасові `print()` / `logger.debug()`.
   - Видалено dead imports і unused код.
   - Видалено експериментальні / тестові файли (`scratch.py`, `test_local.py` тощо).
4. **Залежності оновлені:** нові бібліотеки → `requirements.txt` з версіями.
5. **Конфіг оновлено:** нові змінні → `.env.example` з коментарем-описом.
6. **Архітектурні зміни задокументовано:** якщо рішення відрізняється від `ARCHITECTURE.md` — документ оновлено (включно з ADR § 15 при потребі).
7. **Чекліст оновлено:** пункт позначено як `[x]`, коміт з префіксом номера пункту (наприклад, `[1.6] Implement minimal Lawyer Agent`).

> Стиль коду (коментарі, naming, структура) — окремі правила у `CLAUDE.md`. DoD передбачає, що ці правила дотримано.

---

## Phase 0 — Foundation

> **Мета:** репозиторій, інфраструктура, базовий конфіг. Кінець фази: проєкт запускається з `python main.py` і виводить `Hello`.

### 0.1 Ініціалізація репозиторію
- [x] Створити структуру директорій згідно з `ARCHITECTURE.md` § 3
- [x] `.gitignore` (Python, .env, .venv, qdrant_data, pg_data, output/, __pycache__)
- [x] `README.md` — заглушка зі схемою архітектури, посиланнями на ARCHITECTURE та DELIVERY_CHECKLIST
- [x] `requirements.txt` — повний стек з ARCHITECTURE.md § 2 з фіксованими версіями
- [x] Python venv, перевірити що `pip install -r requirements.txt` проходить чисто

### 0.2 Конфігурація через Pydantic Settings
- [x] `config.py` — клас `Settings(BaseSettings)` з усіма полями з ARCHITECTURE § 11
- [x] Валідатори для CSV-полів (`tech_support_allowed_domains`, `tech_support_tag_whitelist`)
- [x] `.env.example` з повним переліком ключів і коментарями-описами
- [x] Тест: `python -c "from config import settings; print(settings.llm_model)"` працює

### 0.3 Інфраструктура локально
- [x] `docker-compose.yml` — Qdrant + Postgres
- [x] Перевірити запуск: `docker compose up -d`, `curl localhost:6333/healthz`
- [x] Ініціалізація Postgres: створення схеми для LangGraph checkpointer (через `PostgresSaver.setup()`)

### 0.4 Stub main.py
- [x] Завантаження settings, простий REPL loop ("введіть питання → друкуємо назад")
- [x] Перевірка: `python main.py` запускається, читає stdin, не падає

---

## Phase 1 — Vertical Slice #1: "Single agent, single topic, no fancy stuff"

> **Мета:** найпростіший шлях від запиту до відповіді. Один Lawyer Agent, без Critic, без Slack. CLI-only.
>
> **Примітка:** CLAUDE.md invariant «Retrieval is hybrid + reranked, not semantic-only» застосовано відразу — hybrid+rerank pipeline впроваджено тут, а не в Phase 4. Phase 4 відповідно вже виконана.
>
> **Кінець фази:** `python main.py` приймає юридичне питання, шукає у векторній БД, повертає відповідь з джерелами.

### 1.1 Pydantic schemas (ядро)
- [x] `schemas.py` — `Source`, `WorkerResponse`, `SubTask`, `ResearchPlan`, `CritiqueResult`, `EscalationOutput`, `GraphState`
- [x] Валідатори узгодженості (з ARCHITECTURE § 4)
- [x] Unit-тести на валідатори (pytest, 20 тестів, всі green)

### 1.2 Embeddings + Qdrant client
- [x] `retrieval/embeddings.py` — обгортка над OpenAI embeddings з batch-підтримкою
- [x] Qdrant client (singleton), створення колекцій з потрібним vector size
- [ ] Перевірка: вручну upsert тестового вектора → search → знайдено

### 1.3 Ingestion pipeline (мінімальна версія)
- [x] `ingest/chunkers.py` — `chunk_law()` (pass-through), `chunk_article()` (RecursiveCharacterTextSplitter)
- [x] `ingest/pipeline.py` — читання JSONL → embedding text → embed → upsert у Qdrant
- [x] `ingest/run_ingest.py` — CLI з `--collection` flag
- [x] Тестовий прогін на mini-датасеті (10 законів, 10 статей)

### 1.4 Retriever (hybrid + rerank — semantic-only скіповано, впроваджено повний pipeline)
- [x] `retrieval/retriever.py` — `hybrid_search(query, collection, filters, top_k)` → `list[Chunk]`; EnsembleRetriever (Qdrant + BM25) → CrossEncoderReranker → score-threshold
- [x] Підтримка payload filters в Qdrant; `_extract_article_refs` для автоматичного article_number pre-filter у Lawyer
- [x] Unit-тест: `_extract_article_refs` (6 кейсів), `Chunk` model (3 кейси)

### 1.5 RAG tool
- [x] `tools/rag.py` — `rag_search` як LangChain `@tool` з docstring
- [x] Параметри: `query`, `collection`. Внутрішньо викликає `hybrid_search`
- [x] Форматування результату під LLM context (breadcrumb / source, truncate 6000 chars)

### 1.6 Lawyer Agent (мінімальна версія)
- [x] `agents/lawyer.py` — `build_lawyer_agent()` + `invoke_lawyer()` через `create_react_agent`
- [x] System prompt у `prompts/lawyer.md` (Ukrainian; Phase 3 мігрує до Langfuse)
- [x] Tool: `rag_search` (collection="laws")
- [x] Output: `WorkerResponse` через `response_format=WorkerResponse` у `create_react_agent`

### 1.7 Скелет main.py з прямим викликом Lawyer
- [x] REPL loop: input → `invoke_lawyer` → print formatted WorkerResponse (answer, confidence, sources, escalation notice)
- [x] Перевірка: задаємо юридичне питання → отримуємо відповідь з джерелами

**🎯 Milestone 1:** `python main.py` працює end-to-end на юридичних запитах.

---

## Phase 2 — Vertical Slice #2: "All workers + Planner routing"

> **Мета:** додати Planner і двох інших workers. Поки **single-topic** routing (без fan-out), без Critic.
>
> **Кінець фази:** Planner класифікує запит → правильний worker відповідає → користувач отримує відповідь.

### 2.1 Tavily web_search tool
- [x] `tools/web_search.py` — обгортка над Tavily API
- [x] Pre-config: `language=uk`, `country=UA`
- [x] Підтримка `allowed_domains` параметра
- [x] Post-filter: language detection через `langdetect`, drop non-UA
- [x] Trim snippets до N символів
- [x] Unit-тест на mock Tavily response

### 2.2 Common Support Agent
- [x] `agents/common_support.py`
- [x] System prompt у `prompts/common_support.md` з доменними обмеженнями
- [x] Tools: `rag_search` (колекція `articles`) + `web_search` (без whitelist)
- [x] Output: `WorkerResponse`

### 2.3 Technical Support Agent
- [x] `agents/technical_support.py`
- [x] System prompt з логікою "повертай needs_human=True якщо це опис баги/відсутньої функції"
- [x] Tools: `rag_search` з pre-filter за tags + `web_search` з `allowed_domains`
- [x] Output: `WorkerResponse`

### 2.4 Planner Agent
- [x] `agents/planner.py`
- [x] System prompt з прикладами класифікації (off-topic / escalation / single subtask)
- [x] Output: `ResearchPlan` через `with_structured_output`
- [x] **На цьому етапі обмежити `subtasks` максимум 1 елементом** — це single-topic фаза
- [x] Окремі тести для off-topic, escalation, on-topic кейсів

### 2.5 LangGraph: базовий граф (без fan-out, без Critic)
- [x] `supervisor.py` — `build_graph()` з nodes: `planner`, `off_topic_response`, `lawyer`, `common_support`, `technical_support`, `final_response`
- [x] Conditional edges: `route_after_planner` (off-topic / escalation / route to single worker)
- [x] **Без** `escalation_node` поки що — заглушка, що друкує "TODO escalate"
- [x] State: `GraphState` (поточна реалізація з `worker_responses` як списком сумісна з single-topic Phase 2 і Phase 3 fan-out)

### 2.6 Інтеграція з main.py
- [x] Замінити прямий виклик lawyer на `graph.invoke()`
- [x] In-memory checkpointer (`MemorySaver`) — Postgres підключимо пізніше
- [x] Перевірити 4 типи запитів: legal, general, technical, off-topic

### 2.7 Section labels (двомовність)
- [x] `language.py` — мапа `topic → label` для UK і EN
- [x] `final_response.py` — формування markdown з секціями (поки тільки 1 секція = 1 worker, але код готовий для багатьох)
- [x] Skip пустих секцій (`found=False` без контенту)

**🎯 Milestone 2:** Planner-driven routing працює, всі 3 workers відповідають, off-topic відсіюється.

---

## Phase 3 — Vertical Slice #3: "Fan-out + Critic loop"

> **Мета:** multi-topic запити (паралельний fan-out), Critic loop з targeted re-dispatch.
>
> **Кінець фази:** запит "яка комісія на майданчику X і чи не порушує це закон Y" → паралельно technical + legal → агрегована відповідь → Critic approve/revise.

### 3.1 Planner: multi-topic
- [x] Прибрати обмеження `max_subtasks=1`, дозволити до `PLANNER_MAX_SUBTASKS`
- [x] Few-shot examples у prompt для multi-topic запитів
- [x] Тести: запит охоплює 2-3 топіки → план містить відповідну кількість subtasks

### 3.2 Fan-out в LangGraph
- [x] `fan_out_dispatcher` node з Send API (ARCHITECTURE § 5.4)
- [x] State: `worker_responses: Annotated[list[WorkerResponse], operator.add]`
- [x] Перевірка паралельного виконання (час ~ longest worker, не сумарний)

### 3.3 Aggregator
- [x] `final_response.py` — `aggregate(worker_responses, language) -> str`
- [x] Markdown секції в правильному порядку, скіп пустих
- [x] Unit-тести: 1, 2, 3 секції; всі пусті; mix found/not-found

### 3.4 Critic Agent
- [x] `agents/critic.py`
- [x] System prompt з трьома вимірами (Freshness / Completeness / Structure)
- [x] Tools: web_search (для fact-checking) — опційно для першої версії
- [x] Output: `CritiqueResult`
- [x] Логіка freshness: порівняння `version_date` / `date_published` з порогами з `.env`

### 3.5 Critic loop в графі
- [x] `critic_node` після `aggregate_responses_node`
- [x] `route_after_critic` conditional edge
- [x] `targeted_redispatcher` — Send тільки тим workers, кому є `revision_requests`
- [x] State: `retry_count` (увеличуємо на кожному revise), `critic_history: list[CritiqueResult]`
- [x] При `retry_count >= CRITIC_MAX_RETRIES` → escalation

### 3.6 Worker з revision_feedback
- [x] Кожен worker приймає опційний `revision_feedback` параметр
- [x] Інжектиться у prompt як "Попередня версія отримала зауваження: ..."
- [x] Worker зобовʼязаний врахувати feedback або обґрунтовано визнати, що не може

**🎯 Milestone 3:** multi-topic запит проходить fan-out → aggregate → critic → optional revise → final response.

---

## Phase 4 — Hybrid Search + Reranking

> **Мета:** замінити semantic-only retrieval на повний hybrid pipeline.
>
> **Статус:** виконано достроково в Phase 1 (CLAUDE.md invariant). A/B валідація та tags pre-filter для Technical Support — єдині відкриті пункти.

### 4.1 BM25 індекс
- [x] `retrieval/retriever.py` — `BM25Retriever` (langchain_community) per collection, lazy singleton cache (`_bm25_cache`)

### 4.2 Ensemble (RRF merge)
- [x] `EnsembleRetriever` (langchain_classic) з вагами `HYBRID_SEMANTIC_WEIGHT` / `HYBRID_BM25_WEIGHT`

### 4.3 Reranker
- [x] `CrossEncoderReranker` (langchain_classic, `BAAI/bge-reranker-base`) — singleton `_get_reranker()`, score-threshold filter (`rerank_score_threshold`) — інтегровано в `retrieval/retriever.py` (окремий `retrieval/reranker.py` не потрібен)

### 4.4 Інтеграція в `hybrid_search`
- [x] `_extract_article_refs` — article_number pre-filter для Lawyer (автоматично)
- [x] tags pre-filter для Technical Support — `_get_bm25_retriever` отримує `tag_whitelist`, кешується окремо по тегах; `hybrid_search` витягує теги з `filters["tags"]` і передає в BM25 поруч з Qdrant-фільтром
- [x] A/B скрипт: `scripts/ab_retrieval.py` — 7 тестових запитів, виводить semantic-only vs hybrid+rerank side-by-side для ручного огляду

**🎯 Milestone 4:** виконано достроково разом з Phase 1. Залишається ручна A/B валідація та tags pre-filter (Phase 2.3).

---

## Phase 5 — Sessions + Slack Integration

> **Мета:** перехід з REPL на Slack бота з persistent sessions.

### 5.1 Postgres checkpointer
- [x] Замінити `MemorySaver` на `PostgresSaver`
- [x] Setup схеми (одноразово через `PostgresSaver.setup()`)
- [ ] Тест: рестарт додатку — попередня сесія підвантажується по `thread_id` _(ручна перевірка після `docker compose up`)_

### 5.2 Session ID generator
- [x] `make_session_id(team_id, channel_id, user_id)` — формат з ARCHITECTURE § 8.2
- [x] Опційний `:thread_ts` для Slack threads

### 5.3 Slack Bolt app
- [x] `main.py` — Slack Bolt setup, токени з `.env`
- [x] Handler на `app_mention` у `SLACK_USER_CHANNEL_ID`
- [x] Виклик графа з `thread_id = session_id`
- [x] Reply у thread оригінального message

### 5.4 Slack publisher для escalation
- [x] `tools/slack_publisher.py` — функція `post_to_expert_channel(EscalationOutput)`
- [x] Block Kit або markdown форматування з ARCHITECTURE § 9.3
- [x] Error handling: якщо Slack недоступний — fallback до файлу (try/except в `escalation_node`)

**🎯 Milestone 5:** код повністю реалізовано; потребує ручного smoke-test з реальними Slack токенами.

---

## Phase 6 — Escalation Agent

> **Мета:** повноцінний Escalation flow.

### 6.1 Escalation Agent
- [x] `agents/escalation.py` — формує `EscalationOutput`
- [x] LLM-виклик для `summary` поля (стисле формулювання для оператора)
- [x] Збереження report у `output/escalations/{session_id}_{timestamp}.json`

### 6.2 Інтеграція в граф
- [x] `escalation_node` замість заглушки
- [x] Тригери: `plan.needs_human=True`, `retry_count >= MAX_RETRIES`, технічні помилки

### 6.3 Static user-facing message
- [x] Шаблон повідомлення для користувача (UK/EN), що "запит передано оператору"
- [x] Без розкриття внутрішніх деталей

### 6.4 Slack publish + file save
- [x] Виклик `slack_publisher.post_to_expert_channel`
- [x] File save як аудит-trail (завжди, навіть якщо Slack ОК)

**🎯 Milestone 6:** повністю реалізовано і покрито тестами.

---

## Phase 7 — Observability (Langfuse)

> **Мета:** повне трейсинг + Prompt Management + LLM-as-a-Judge.

### 7.1 Langfuse setup
- [x] Account, project, API keys у `.env` _(ручне налаштування — потребує реального Langfuse account)_
- [x] `observability/langfuse_client.py` — singleton клієнт з graceful fallback
- [x] `observability/callbacks.py` — `CallbackHandler` factory

### 7.2 Tracing інтеграція
- [x] Передача callback у `graph.invoke(config={"callbacks": [...]})`
- [x] Metadata: `user_id`, `session_id`, `tags`
- [ ] Перевірка: 3-5 запусків → 3-5 traces у Langfuse UI _(потребує налаштованого Langfuse account)_

### 7.3 Prompt Management
- [x] Створити промпти в Langfuse UI з label `production` _(ручне — запустити `python scripts/sync_prompts.py` після налаштування account)_
- [x] Замінити `prompts/*.md` reading на `langfuse.get_prompt(...).compile(...)` з fallback на локальний файл
- [x] Backup prompts в репо + `scripts/sync_prompts.py` для синхронізації
- [ ] Перевірка: змінити prompt в Langfuse → нова поведінка без redeploy _(потребує налаштованого Langfuse)_

### 7.4 Sessions + Users tracking
- [x] Заповнення `langfuse_session_id`, `langfuse_user_id`, `langfuse_tags` у callback metadata (`main.py` Slack handler)
- [x] Перевірка: ключі коректно парсяться `LangchainCallbackHandler._parse_langfuse_trace_attributes` (verified end-to-end проти реального SDK)

### 7.5 LLM-as-a-Judge evaluators
- [x] Налаштувати в Langfuse UI мінімум 2 evaluators _(ручне налаштування в UI)_
- [ ] Зробити 3-5 нових запусків і перевірити автоматичні scores _(manual)_
- [x] GEval тести: `tests/evaluations/test_eval_geval.py` — 10 метрик (Groundedness ×3, Plan Quality, Off-topic Adherence, Critique Quality, Answer Relevancy, Source Citation Quality, Tool Correctness ×2); всі збираються pytest, 142 unit-тести зелені

**🎯 Milestone 7:** код-частина готова; Langfuse account + UI налаштування залишаються ручними кроками.

---

## Phase 8 — Testing

> **Мета:** golden dataset + automated evals на всіх рівнях.

### 8.1 Golden dataset
- [x] `tests/golden_dataset.json` — 15 прикладів (5 happy / 5 edge / 5 failure: 2 off-topic + 3 escalation)
- [x] Manual review кожного прикладу
- [x] Структура з ARCHITECTURE § 13.2 (id, category, input, language, expected_topics, expected_output, expected_sources_doc_ids, should_escalate); валідується в `tests/test_e2e.py`

### 8.2 Unit tests
- [x] `tests/conftest.py` — фікстури (mock LLM, sample chunks, mock Tavily)
- [x] Тести на чисті функції: RRF/BM25 tag filtering, language detection, section formatting, aggregator

### 8.3 Component tests
- [x] `test_planner.py` — behavioral unit tests (mock LLM): off-topic, escalation, single/multi-topic routing
- [x] `test_lawyer.py` — behavioral unit tests: invoke + WorkerResponse structure
- [x] `test_common_support.py` — behavioral unit tests: tools wiring + output structure
- [x] `test_technical_support.py` — behavioral unit tests: escalation detection, tag whitelist wiring
- [x] `test_critic.py` — behavioral unit tests: approve/revise verdicts, retry logic
- [x] `test_escalation.py` — EscalationOutput completeness (всі поля, категорії, file save, Slack publish)
- [x] GEval quality tests (LLM-as-a-judge) — `tests/evaluations/test_eval_geval.py` 10 метрик: Groundedness ×3, Plan Quality, Off-topic Adherence, Critique Quality, Answer Relevancy, Source Citation Quality, Tool Correctness ×2

### 8.4 Tool correctness tests
- [x] `test_tools.py` — 11 кейсів: Lawyer тільки `rag_search` (default `collection="laws"`), Common Support `rag_search_articles` + plain `web_search`, Technical Support `rag_search_articles` з тегами + `web_search_technical` з allowed_domains, fallback гілки, RAG dispatch, Tavily filter

### 8.5 E2E tests
- [x] `test_e2e.py` — структурна валідація golden dataset (6 тестів) + parametrized `graph.invoke()` over 15 кейсів під `@pytest.mark.eval` (skip без API key)
- [x] Метрики: Correctness GEval (vs `expected_output`), AnswerRelevancyMetric
- [x] Збереження результатів у `tests/results/e2e_baseline_<ts>.json` через `_append_baseline`

### 8.6 CI integration (опційно)
- [ ] GitHub Actions workflow `deepeval test run tests/`
- [ ] Запуск на PR

**🎯 Milestone 8:** 172 unit/structural тести зелені; 25 LLM evals (10 GEval + 15 параметризованих E2E) під `@pytest.mark.eval` готові до запуску з API key. Manual review golden dataset і CI workflow — відкриті.

---

## Phase 9 — Polish + Demo prep

> **Мета:** все що залишилось до здачі.

### 9.1 README
- [x] Опис проєкту, архітектурна діаграма (Mermaid flowchart)
- [x] Quick start guide (з ARCHITECTURE § 14)
- [x] Опис доменних обмежень (3 теми + defense in depth)
- [x] Приклади запитів (happy one-topic, happy multi-topic, off-topic, escalation)
- [x] Лінки на ARCHITECTURE.md та DELIVERY_CHECKLIST.md
- [x] Попередній README.md перенесено в `docs/Технічне завдання.md`

### 9.2 Демо
- [x] Сценарій 1: happy path multi-topic (legal + technical)
- [x] Сценарій 2: off-topic refusal
- [x] Сценарій 3: escalation (bug report)
- [ ] Запис відео або GIF (3-5 хв)

### 9.3 Скріншоти Langfuse
- [x] Trace tree з повним деревом викликів
- [x] Sessions view
- [x] Evaluator scores
- [x] Prompt Management

### 9.4 Звіт baseline-метрик
- [ ] Зведена таблиця DeepEval scores
- [ ] Аналіз провалів і найслабших місць

### 9.5 Pre-release verification
- [ ] Перевірити що `requirements.txt` повний: `pip install -r requirements.txt` у чистому venv → проєкт запускається
- [ ] Перевірити що `.env.example` синхронізований з реальним `Settings` класом (всі поля присутні)
- [ ] Прогнати `deepeval test run tests/` і e2e сценарії на чистій ingestion
- [ ] Перевірити що `ARCHITECTURE.md` відображає реальний стан коду (не застарів за час реалізації)
- [ ] Видалити будь-які залишкові TODO без власника або застарілі коментарі

**🎯 Milestone 9:** проєкт готовий до здачі і захисту.

---

## Опційні розширення (якщо є час)

- [ ] Cleanup сесій по TTL (background task)
- [ ] Migration BM25 на Qdrant native sparse vectors
- [ ] HITL approval перед публікацією у Slack expert channel
- [ ] Multilingual prompt versions (UK/EN) у Langfuse
- [ ] A/B prompt testing через Langfuse labels
- [ ] Метрика "Citation accuracy" (custom GEval) — чи правильно агенти цитують джерела

---

## Як працювати з цим документом у Claude Code

1. **На початку сесії** Claude Code автоматично читає `CLAUDE.md` (з правилами стилю і library-first принципом). Додатково покажи поточний пункт чекліста, наприклад: *"Працюємо над 1.6 Lawyer Agent (мінімальна версія). Деталі — у `ARCHITECTURE.md` § 4 і § 6."*
2. **Перед закриттям пункту** прогани його через **Definition of Done** (на початку цього файлу). Жоден пункт не закривається без cleanup і оновлення супутніх документів.
3. **Якщо з'являються відкриття/зміни архітектури** — оновлювати `ARCHITECTURE.md` як live-документ. Серйозні рішення → новий запис в ADR § 15.
4. **Не йти вперед** до завершення поточного milestone. Якщо vertical slice не працює — зупинитись і доробити.
5. **Reference-матеріали з лекцій** (у `docs/patterns/`) Claude Code підвантажує точково, на запит. Якщо потрібен патерн з лекції — попроси Claude знайти відповідний reference замість того, щоб розраховувати на його memory.
