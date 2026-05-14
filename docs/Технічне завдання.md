# Система підтримки користувачів електронної системи публічних закупівель України

## Опис

Мультиагентна система для обробки запитів користувачів електронної системи публічних закупівель України (далі — ЕСЗ). Система спеціалізується на трьох доменах:

1. **Технічна робота** з ЕСЗ та електронними майданчиками (як виконати дію в системі).
2. **Процедури проведення закупівель** (як правильно провести закупівлю згідно з регламентом).
3. **Законодавство та нормативні акти** (як вчинити правильно з точки зору закону).

Запити, що виходять за межі цих доменів, відхиляються. Запити, які система не може обробити автоматично (баги, ідеї покращення, складні випадки), ескалюються до людини-оператора через окремий Slack-канал.

**Мова комунікації:** українська (основна) та англійська. Web-пошук виконується виключно українською мовою.

## Архітектурний патерн

**Основний патерн:** Orchestrator-Workers + Evaluator-Optimizer (Anthropic).

- **Orchestrator-Workers:** Supervisor (orchestrator) делегує підзадачі спеціалізованим агентам (workers) — потенційно паралельно (fan-out), якщо запит охоплює кілька доменів.
- **Evaluator-Optimizer:** Critic оцінює сформовану відповідь і запускає цикл доопрацювання (revise loop) до досягнення якості або вичерпання ліміту ітерацій.

**Тип взаємодії:** ієрархічна з планувальним шаром. Planner декомпозує запит у структурований план, Supervisor виконує план через workers і Critic, та повертає агреговану відповідь. Ключовий виклик: якість декомпозиції на Planner і якість критики на Critic визначають загальну якість системи.

## Доменні обмеження

Система **відповідає виключно** на питання, що стосуються:
- технічної роботи з ЕСЗ та електронними майданчиками;
- процедур проведення публічних закупівель в Україні;
- законодавства та нормативно-правових актів у сфері публічних закупівель.

**Defense in depth (трирівневий захист від off-topic):**

1. **Planner gate** — Planner повертає `is_on_topic: bool`. Якщо `false`, Supervisor завершує цикл і повертає користувачу повідомлення про обмеження доменом.
2. **System prompts** — кожен агент у своєму system prompt має чітку директиву: "Ти відповідаєш виключно на питання, повʼязані з публічними закупівлями України. Якщо запит виходить за межі — поверни порожній результат із позначкою off-topic."
3. **Critic guardrail** — Critic у вимірі Structure валідує, що фінальна відповідь не містить відповідей на питання поза доменом, навіть якщо ті проскочили попередні фільтри.

## Агенти та інструменти

### Supervisor Agent

**Роль:** оркеструє увесь pipeline обробки запиту, приймає рішення на основі результатів Planner та Critic, керує сесіями.

**Поведінка:**
- Завжди починає з виклику Planner.
- Якщо Planner повертає `is_on_topic=false` — повертає користувачу повідомлення про обмеження доменом, цикл завершується.
- Якщо Planner повертає `needs_human=true` — одразу делегує до Escalation Agent (без запуску workers і Critic).
- Якщо план містить підзадачі — паралельно делегує їх відповідним worker-агентам (fan-out).
- Збирає результати від workers, формує агреговану відповідь по секціях.
- Передає агреговану відповідь Critic.
- На основі вердикту Critic: `approve` → повертає користувачу; `revise` → запускає доопрацювання тих workers, до яких є зауваження.
- Контролює retry-ліміт. Після його вичерпання — ескалація.
- Управляє сесіями користувача через LangGraph checkpointer (Postgres).

**Інструменти:** делегування до інших агентів через LangGraph nodes (не tool-calls).

### Planner Agent

**Роль:** декомпозує запит користувача у структурований план, фільтрує off-topic запити, ідентифікує запити, що потребують людини.

**Поведінка:**
- Класифікує запит за темами (одна або кілька з: `technical_system`, `procurement_general`, `legal`).
- Виявляє off-topic запити (`is_on_topic=false`).
- Виявляє запити, що одразу потребують ескалації: чітко описана бага системи, запит на функцію, якої система не має, або заявка на покращення (`needs_human=true`).
- Повертає структурований план у форматі `ResearchPlan` (Pydantic).

**Інструменти:** LLM structured output (`ResearchPlan`).

### Lawyer Agent

**Роль:** відповідає на питання "як правильно вчинити відповідно до закону".

**Поведінка:**
- Активується для підзадач з topic `legal`.
- Шукає виключно у векторній колекції `laws` (закони та нормативні акти).
- Якщо релевантної інформації не знайдено — повертає `found=false`, не намагається доповнити з інших джерел.

**Інструменти:** RAG (semantic search по колекції `laws`).

### Common Support Agent

**Роль:** відповідає на питання "як це працює" (процедури, регламенти, тарифи, політика повернень).

**Поведінка:**
- Активується для підзадач з topic `procurement_general`.
- Шукає у векторній колекції `articles` (статті, FAQ, документація сервісу).
- За потреби доповнює пошуком в інтернеті (Tavily, лише UA).

**Інструменти:** RAG (semantic search по колекції `articles`), Web Search (Tavily).

### Technical Support Agent

**Роль:** відповідає на питання "як виконати конкретну дію в системі чи на майданчику".

**Поведінка:**
- Активується для підзадач з topic `technical_system`.
- Шукає у векторній колекції `articles` з пре-фільтром за `tags` (whitelist у `.env`) та в інтернеті по whitelist-у доменів технічної документації майданчиків.
- Якщо нічого не знайдено і запит виглядає як опис баги/відсутньої функції — повертає прапорець, що потребує людської валідації (це підхопить Critic або Supervisor як сигнал до ескалації).

**Інструменти:** RAG (semantic search по колекції `articles` з пре-фільтром за `tags`), Web Search (Tavily з `allowed_domains` whitelist).

### Critic Agent

**Роль:** оцінює якість агрегованої відповіді через незалежну верифікацію та повертає вердикт.

**Поведінка:**
- Активується для відповідей від Lawyer / Common Support / Technical Support агентів (одного або кількох — у випадку fan-out).
- **НЕ активується** для off-topic та для прямої ескалації від Planner.
- Оцінює відповідь по трьох вимірах:
  1. **Freshness** — чи базуються знахідки на актуальних даних? Чи є ознаки застарілої інформації (особливо критично для законодавства)?
  2. **Completeness** — чи повністю покрито всі підзадачі з плану? Чи є непокриті аспекти?
  3. **Structure** — чи відповідь чітко структурована, чи дотримано формату секцій, чи немає off-topic вкраплень?
- Повертає `CritiqueResult(verdict, gaps, revision_requests)`.
- На `revise` вказує **які саме секції/підзадачі** потребують доопрацювання — Supervisor перезапускає лише відповідних workers, не весь цикл.

**Інструменти:** LLM structured output (`CritiqueResult`). Опційно — Web Search для fact-checking (рекомендується для виміру Freshness).

### Escalation Agent

**Роль:** обробляє критичні випадки, де автоматична відповідь неможлива або непотрібна.

**Тригери ескалації:**
- Planner ідентифікував багу системи / ідею покращення / запит на нову функцію (`needs_human=true`).
- Critic тричі поспіль (або інший ліміт з `.env`) повернув `revise` — система не може досягти якісної відповіді.
- Технічна помилка в pipeline.

**Поведінка:**
- Формує `EscalationOutput` з повним контекстом (оригінальний запит, plan, всі відповіді workers, critic feedback, причина ескалації).
- Зберігає escalation report у файл (audit trail).
- Надсилає нотифікацію в експертний Slack-канал з повним контекстом.
- Користувачу повертає **статичне повідомлення-інформування**, що запит буде оброблено людиною (HITL approval не використовується).

**Інструменти:** Slack API (publish у експертний канал), File System tool (збереження report).

## Structured Output контракти (Pydantic)

```python
class SubTask(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    query: str               # перефразований під цей topic суб-запит
    rationale: str           # чому Planner так розклав

class ResearchPlan(BaseModel):
    is_on_topic: bool
    off_topic_reason: str | None
    language: Literal["uk", "en"]
    original_query: str
    subtasks: list[SubTask]  # 0 якщо off-topic, 1+ якщо on-topic
    needs_human: bool        # пряма ескалація: бага / ідея / нова фіча
    escalation_reason: str | None

class WorkerResponse(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    found: bool
    answer: str | None
    sources: list[str]
    confidence: float
    needs_human: bool = False         # для technical_support: бага виявлена
    needs_human_reason: str | None = None

class CritiqueResult(BaseModel):
    verdict: Literal["approve", "revise"]
    freshness_score: float            # 0-1
    completeness_score: float         # 0-1
    structure_score: float            # 0-1
    gaps: list[str]                   # перелік виявлених проблем
    revision_requests: list[dict]     # [{topic, request}] — кому що переробити

class EscalationOutput(BaseModel):
    summary: str
    category: Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]
    customer_message: str
    attempted_resolution: str
    full_context: dict                # plan + worker responses + critic history
```

## База знань для RAG

**Векторна БД:** Qdrant. Дві колекції (`laws` та `articles`) в одному інстансі — спільна інфраструктура, спільний embedding-pipeline, але різні стратегії chunking та фільтрації.

**Чому Qdrant:** нативна підтримка metadata-фільтрації (payload filters) перед vector search, що критично для нашої архітектури з пре-фільтрами (`article_number`, `tags`); production-ready з моменту першого запуску; добре інтегрований з LangChain.

### Колекція `laws`

Закони та нормативно-правові акти у сфері публічних закупівель.

**Стратегія chunking:** великі чанки на рівні структурного елементу документа (стаття / частина статті / параграф), щоб зберігати юридичний контекст цілісним. Розрізати статтю на дрібні фрагменти не можна — втрачається змістова повнота.

**Схема метаданих:**

| Поле | Тип | Призначення |
|---|---|---|
| `id` | string | Унікальний ID chunk-а |
| `doc_id` | string | ID документа (спільний для всіх chunks одного закону) |
| `title` | string | Назва документа (наприклад, *"КУпАП, стаття 164-14 «Порушення законодавства про закупівлі»"*) |
| `type` | string | Тип документа (`code_article`, `law`, `regulation`, ...) |
| `authority` | string | Орган, що видав (наприклад, `Верховна Рада України`) |
| `domain` | string | Тематичний домен (наприклад, `administrative_liability_procurement`) |
| `source` | string | Короткий лейбл джерела (наприклад, `zakon.rada.gov.ua`) |
| `source_url` | string | Повна URL для цитування у відповіді |
| `version_date` | date | Дата редакції документа — критично для Freshness-перевірок Critic |
| `date_fetched` | datetime | Коли документ завантажений у KB |
| `breadcrumb` | string | Готовий контекстний ідентифікатор (наприклад, *"КУпАП, стаття 164-14 «...», редакція від 03.05.2026"*) — використовується у відповіді як human-readable джерело |
| `section_heading` | string | Заголовок секції, до якої належить chunk |
| `article_number` | string | Номер статті (для прямого пошуку за номером) |
| `part_number` | string \| null | Номер частини статті |
| `paragraph_number` | string \| null | Номер параграфа |
| `section_index` | int | Індекс секції в документі |
| `chunk_index` | int | Індекс chunk-а в межах секції |
| `text` | string | Власне текст chunk-а |

**Що векторизуємо:** конкатенацію `breadcrumb + section_heading + text`. Це закладає юридичний контекст в embedding і покращує retrieval за номерами статей (запит "стаття 164-14 КУпАП" знаходить релевантний chunk навіть без точного збігу слів).

### Колекція `articles`

Статті, FAQ, методичні матеріали, технічна документація сервісу та майданчиків.

**Стратегія chunking:** менші чанки (~500-800 токенів) з overlap ~100 токенів — стандартний `RecursiveCharacterTextSplitter`.

**Схема метаданих:**

| Поле | Тип | Призначення |
|---|---|---|
| `id` | string | Унікальний ID chunk-а |
| `doc_id` | string | ID документа |
| `title` | string | Назва статті |
| `type` | string | Тип контенту (`article`, `faq`, `tutorial`, ...) |
| `date_published` | datetime | Дата публікації — для Freshness |
| `tags` | list[string] | Теги (наприклад, `["роботи", "предмет закупівлі", "планування"]`) |
| `source` | string | Лейбл джерела (наприклад, `Prozorro`) — за замовчуванням, можна додати під час ingestion |
| `source_url` | string \| null | URL оригіналу — за замовчуванням |
| `chunk_index` | int | Індекс chunk-а |
| `text` | string | Текст chunk-а |

**Що векторизуємо:** конкатенацію `title + tags(joined) + text`. Теги додають семантичні якорі і покращують retrieval за тематичними запитами.

### Маршрутизація запитів агентів

| Агент | Колекція | Стратегія фільтрації |
|---|---|---|
| **Lawyer Agent** | `laws` (виключно) | Без додаткової фільтрації; за наявності в запиті номера статті — пре-фільтр за `article_number` перед vector search |
| **Common Support Agent** | `articles` | Без фільтра або з опційним пре-фільтром за `tags` |
| **Technical Support Agent** | `articles` | Пре-фільтр за `tags` (whitelist у `.env` `TECH_SUPPORT_TAG_WHITELIST` — **TODO: точний перелік тегів формується після аналізу повного датасету статей**) |

**Приклад пре-фільтрації:** для запиту *"яка відповідальність за порушення статті 164-14"* Lawyer Agent спочатку фільтрує метадатою `article_number == "164-14"`, потім — vector search всередині звуженої вибірки. Це різко підвищує precision і скорочує latency.

### Hybrid Search + Reranking

Кожен RAG-пошук проходить трьохступеневу обробку:

**1. Hybrid retrieval (semantic + BM25):**
- **Semantic search** — vector search у Qdrant за cosine similarity.
- **BM25 search** — лексичний пошук за ключовими словами (бібліотека `rank_bm25`).
- **Ensemble** — об'єднання результатів через зважений Reciprocal Rank Fusion (RRF) або через `EnsembleRetriever` з LangChain. Ваги налаштовуються через `.env` (`HYBRID_SEMANTIC_WEIGHT`, `HYBRID_BM25_WEIGHT`).

**Чому hybrid:** semantic ловить смислові збіги (*"чому списали гроші"* → FAQ про автопродовження підписки), BM25 ловить точні терміни і числа (*"стаття 164-14"*, *"ДБН А.2.2-3:2014"*). Для законодавчого домену з великою кількістю номерів статей, кодів класифікаторів і назв нормативних актів — це must-have.

**2. Top-K retrieval:**
- На етапі hybrid retrieval повертаємо `RETRIEVAL_TOP_K` кандидатів (наприклад, 20).
- Це широке "сітка" — далі звужуємо reranker-ом.

**3. Cross-encoder reranking:**
- Модель: `BAAI/bge-reranker-base` (або `bge-reranker-v2-m3` для кращої якості за ціною latency).
- Reranker оцінює пари `(query, candidate)` і повертає precision-orієнтовані scores.
- Залишаємо `RERANK_TOP_K` найкращих (наприклад, 5).
- Кандидати з score нижче `RERANK_SCORE_THRESHOLD` відкидаються — це і є фільтр шуму.

**Архітектурний layout:**

```
query → [pre-filter by metadata]
      → semantic search (top 20)  ─┐
      → BM25 search (top 20)       ├─ Ensemble (RRF) → top 20
      →                            ─┘
      → cross-encoder reranker → top 5 (above threshold)
      → return chunks + scores
```

**Реалізація:** окремий модуль `retriever.py` з єдиним інтерфейсом `hybrid_search(query, collection, filters, top_k) -> list[Chunk]`. Усі агенти викликають через цей інтерфейс — нікому не треба знати про BM25 чи reranker.

### Формування sources у відповіді

При формуванні відповіді worker-агенти повертають `sources: list[str]`. Формат залежить від колекції:

- Для `laws`: використовуємо `breadcrumb` + `source_url` → у відповіді показуємо як `[КУпАП, стаття 164-14, редакція від 03.05.2026](https://zakon.rada.gov.ua/...)`.
- Для `articles`: використовуємо `title` + `source_url` (або `source` якщо URL відсутній) → `[Порядок визначення предмета закупівлі — Prozorro](https://...)`.

**Дедуплікація:** якщо retrieval повернув кілька chunks одного документа (за `doc_id`), у sources вказуємо документ **один раз**.

### Freshness signals для Critic

Critic під час оцінки виміру Freshness використовує:

- Для `laws`: `version_date` — якщо найсвіжіший знайдений документ старший за `LAWS_FRESHNESS_THRESHOLD_DAYS` (з `.env`), додає попередження у `gaps`. Для законодавства це критично — застаріла редакція може давати неправильну юридичну пораду.
- Для `articles`: `date_published` — поріг `ARTICLES_FRESHNESS_THRESHOLD_DAYS`. Менш критично, але корисно для технічних статей про інтерфейс майданчиків (там часто змінюються UI-флоу).

### Готові датасети (від користувача)

- **Закони** — нормативна база у форматі, що відповідає схемі колекції `laws` (вже з `breadcrumb`, `article_number`, `version_date` тощо).
- **Статті** — матеріали внутрішнього сервісу про публічні закупівлі у форматі колекції `articles` (з `tags`, `date_published`).

**Ingestion-пайплайн** (`ingest.py`) приймає JSONL/JSON-файли з готовими метаданими, виконує лише chunking (якщо потрібно) + embedding + upsert у векторну БД. Без OCR, без парсингу сирих PDF — це вже зроблено upstream.

## Web Search

**Бекенд:** Tavily API.

**Конфігурація:**
- Мова пошуку: `language=uk`, `country=UA`.
- Пост-фільтр результатів за мовою (через `langdetect` або LLM-фільтр у tool wrapper) — викидаємо не-UA результати.
- Для Technical Support Agent — параметр `allowed_domains` (whitelist доменів технічної документації майданчиків).

**Доступ:**
- Common Support Agent — Tavily без обмежень доменів.
- Technical Support Agent — Tavily з `allowed_domains` whitelist.
- Critic — Tavily для fact-checking (опційно).

## Сесії та память

**Backend:** PostgreSQL через `langgraph-checkpoint-postgres` (`PostgresSaver`).

**Session ID:** комбінація `team_id:channel_id:user_id` (для Slack-інтеграції) або `:thread_ts` для тримання контексту в threads.

**TTL сесії:** автоматичне закриття після N годин неактивності (значення в `.env`). Нова сесія = новий `thread_id`.

## Workflow (LangGraph)

```
START
  │
  ▼
Supervisor → Planner
  │
  ├─ if is_on_topic=false       → STATIC off-topic message → END
  ├─ if needs_human=true        → Escalation Agent → END
  │
  ▼
Fan-out по subtasks (паралельно):
  ├─ Lawyer Agent          (для topic=legal)
  ├─ Common Support Agent  (для topic=procurement_general)
  └─ Technical Support Agent (для topic=technical_system)
  │
  ▼
Aggregate by sections
  │
  ▼
Critic
  │
  ├─ if approve  → final response → END
  ├─ if revise && retries < N
  │     → re-run targeted workers with feedback → Aggregate → Critic
  └─ if revise && retries == N → Escalation Agent → END
```

**Агрегація відповіді** — простий збирач секцій (без LLM-виклику). Секції з порожніми відповідями (`found=false` без контенту) **не показуються** користувачу. Формат:

```markdown
### Юридичний аспект
[відповідь Lawyer Agent]

### Загальна процедура
[відповідь Common Support Agent]

### Технічна реалізація
[відповідь Technical Support Agent]
```

## Конфігурація через .env

Усі параметри додатку виносяться в `.env` через **Pydantic Settings** (`BaseSettings`). У репозиторії — `.env.example` із заглушками і повним переліком.

**Мінімальний перелік:**

```
# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small

# Web search
TAVILY_API_KEY=...
TECH_SUPPORT_ALLOWED_DOMAINS=domain1.ua,domain2.ua,...
TECH_SUPPORT_TAG_WHITELIST=майданчик,інтерфейс,tutorial

# Vector DB (Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
QDRANT_LAWS_COLLECTION=laws
QDRANT_ARTICLES_COLLECTION=articles
LAWS_FRESHNESS_THRESHOLD_DAYS=180
ARTICLES_FRESHNESS_THRESHOLD_DAYS=365

# Hybrid retrieval
RETRIEVAL_TOP_K=20
HYBRID_SEMANTIC_WEIGHT=0.6
HYBRID_BM25_WEIGHT=0.4

# Reranking
RERANKER_MODEL=BAAI/bge-reranker-base
RERANK_TOP_K=5
RERANK_SCORE_THRESHOLD=0.3

# Postgres (sessions)
POSTGRES_URL=postgresql://...
SESSION_TTL_HOURS=24

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_USER_CHANNEL_ID=C...
SLACK_EXPERT_CHANNEL_ID=C...

# Agent behavior
CRITIC_MAX_RETRIES=3
WORKER_TIMEOUT_SECONDS=60
PLANNER_MAX_SUBTASKS=3

# Observability
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=...
```

## Інтеграція зі Slack

**Два канали:**

1. **Користувацький канал** — користувач задає питання, бот відповідає (агрегована відповідь або статичне off-topic / escalation повідомлення).
2. **Експертний канал** — Escalation Agent публікує повідомлення з повним контекстом для людини-оператора.

**Контракт повідомлення в експертний канал:**
- Оригінальний запит
- Категорія ескалації (bug / feature_request / unanswerable / max_retries_exceeded)
- Структурований план (від Planner)
- Спроби workers (повний контекст)
- Critic feedback (якщо ескалація після max_retries)
- Suggested next steps

## Моніторинг та тестування

### Langfuse (обов'язково)

Кожен запуск pipeline трейситься в Langfuse:
- Дерево викликів усіх агентів і tools (Planner → workers → Critic → Escalation).
- Latency, токени, cost для кожного LLM-виклику.
- Metadata: agent name, topic, urgency, confidence, session_id, retry count.
- Sessions і users tracking.
- System prompts усіх агентів винесено в Langfuse Prompt Management — у коді жодного захардкодженого промпту.
- Online evaluation через LLM-as-a-Judge (мінімум 2 evaluators).

### Тестування через DeepEval

**Golden dataset:** 15-20 прикладів (happy path + edge cases + failure cases) у `tests/golden_dataset.json`.

**Component tests:**

| Компонент | Що тестується | Метрика |
|---|---|---|
| Planner | Правильна класифікація topic, виявлення off-topic, виявлення needs_human | GEval (Plan Quality) + Tool Correctness |
| Lawyer Agent | Знаходить релевантні закони, не галюцинує, повертає `found=false` коли треба | Groundedness (GEval) |
| Common Support Agent | Знаходить релевантні статті, відповідь підкріплена джерелами | Groundedness + Answer Relevancy |
| Technical Support Agent | Правильно визначає коли потрібна ескалація на людину | Tool Correctness + GEval |
| Critic | Виявляє реальні gaps, формулює дієві revision_requests, не пропускає off-topic | GEval (Critique Quality) |
| Escalation | EscalationOutput містить повний контекст для оператора | GEval (Escalation Completeness) |

**End-to-end tests** на golden dataset з метриками:
- Correctness (GEval)
- Answer Relevancy
- Citation Presence (custom GEval)

**Запуск:** `deepeval test run tests/`.

## Структура проєкту

```
procurement-support/
├── main.py                  # Entry point — Slack bot + REPL fallback
├── supervisor.py            # Supervisor logic + LangGraph definition
├── agents/
│   ├── planner.py
│   ├── lawyer.py
│   ├── common_support.py
│   ├── technical_support.py
│   ├── critic.py
│   └── escalation.py
├── tools/
│   ├── rag.py               # RAG search by collection
│   ├── web_search.py        # Tavily wrapper з UA-фільтром
│   └── slack.py             # Slack publishing
├── retriever.py             # Hybrid search + reranking
├── ingest.py                # Ingestion pipeline → laws + articles collections
├── schemas.py               # Pydantic models (ResearchPlan, CritiqueResult, ...)
├── final_response.py        # Aggregator: workers → user-facing response
├── config.py                # Pydantic Settings — all .env vars
├── prompts/                 # Backup промптів (live версія в Langfuse)
├── tests/
│   ├── golden_dataset.json
│   ├── test_planner.py
│   ├── test_lawyer.py
│   ├── test_common_support.py
│   ├── test_technical_support.py
│   ├── test_critic.py
│   ├── test_escalation.py
│   └── test_e2e.py
├── data/                    # Source documents для ingestion
│   ├── laws/
│   └── articles/
├── output/                  # Escalation reports
├── requirements.txt
├── .env.example
└── README.md
```

## Що здавати

- Вихідний код у Git-репозиторії.
- README з діаграмою архітектури, інструкцією запуску, описом доменних обмежень, прикладами використання.
- `.env.example` з повним переліком змінних.
- Записане демо роботи системи (відео або GIF) — мінімум 3 сценарії: happy path, off-topic refusal, escalation.
- Скріншоти Langfuse: trace tree, session, evaluator scores, prompt management.
- Тести (DeepEval) з результатами запуску.
- Звіт про baseline-метрики системи.

## Відкриті питання та TODO

Перелік пунктів, які залишаються відкритими і будуть закриті під час імплементації:

1. **Tag whitelist для Technical Support Agent** (`TECH_SUPPORT_TAG_WHITELIST`) — точний перелік тегів формується після аналізу повного датасету колекції `articles`. Початковий варіант — на око, з подальшим уточненням за результатами тестів.
2. **Web search domain whitelist для Technical Support Agent** (`TECH_SUPPORT_ALLOWED_DOMAINS`) — список доменів технічної документації майданчиків формує користувач (надасть пізніше).
3. **Embedding-модель** — `text-embedding-3-small` як baseline; якщо якість retrieval недостатня — переходити на `text-embedding-3-large` (через зміну `EMBEDDING_MODEL` у `.env`).
4. **Reranker model** — стартуємо з `BAAI/bge-reranker-base`; якщо якість недостатня — `bge-reranker-v2-m3` (за ціною latency).
5. **Hybrid search ваги** (`HYBRID_SEMANTIC_WEIGHT` / `HYBRID_BM25_WEIGHT`) — стартові 0.6 / 0.4; калібрувати на golden dataset.
6. **Freshness thresholds** — стартові значення (180 днів для законів, 365 для статей) можуть бути переглянуті залежно від характеру датасету.
7. **TTL сесії** (`SESSION_TTL_HOURS`) — стартове значення 24 години, переглянути за результатами реального використання.
8. **Структура повідомлення в експертний Slack-канал** — точний формат (Block Kit / простий markdown) визначити під час імплементації Slack-інтеграції.