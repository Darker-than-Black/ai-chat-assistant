# Архітектура системи

> **Контекст документа:** ця архітектурна довідка доповнює `project_support.md` (ТЗ — *що* і *чому*). Тут — *як* саме збудовано систему: модулі, контракти між ними, потоки даних, технологічні рішення.

---

## 1. Огляд системи

Мультиагентна система підтримки користувачів електронної системи публічних закупівель України. Реалізує патерн **Orchestrator-Workers + Evaluator-Optimizer** на базі LangGraph.

**Точки входу:**
- Slack бот (основна) — два канали (користувацький + експертний).
- CLI/REPL (для розробки і дебагу).

**Зовнішні залежності:**
- LLM провайдер (OpenAI / Anthropic).
- Tavily API (web search).
- Qdrant (vector DB).
- PostgreSQL (sessions checkpointer).
- Slack API.
- Langfuse (observability).

---

## 2. Технологічний стек

| Шар | Технологія | Версія | Призначення |
|---|---|---|---|
| Runtime | Python | 3.11+ | Основна мова |
| Конфіг | Pydantic Settings | 2.x | Усі налаштування з `.env` |
| Структуровані контракти | Pydantic | 2.x | Усі inter-agent повідомлення |
| Агентний фреймворк | LangChain + LangGraph | latest | Граф агентів, checkpointer, HITL |
| LLM SDK | langchain-openai / langchain-anthropic | latest | Виклики моделі |
| Vector DB | Qdrant | latest | RAG storage з payload-фільтрацією |
| Embeddings | OpenAI text-embedding-3-small | — | Векторизація |
| BM25 | rank_bm25 | latest | Лексичний пошук |
| Reranker | sentence-transformers + bge-reranker-base | latest | Cross-encoder reranking |
| Web search | Tavily API | — | Пошук в інтернеті |
| Sessions | langgraph-checkpoint-postgres | latest | Persistent memory |
| Slack | slack-sdk / slack-bolt | latest | Two-channel integration |
| Observability | langfuse | latest | Tracing + Prompt Mgmt + LLM Judge |
| Тестування | deepeval + pytest | latest | Component + e2e evals |
| Мова detection | langdetect | latest | Web search results filter |

### 2.1 Принципи використання стеку

> Розгорнуті правила роботи з кодом — у `CLAUDE.md`. Тут — стек-специфічні наслідки.

**Library-first.** Кожен компонент стеку обрано тому, що дає готове рішення для нашої задачі. Перш ніж писати власну логіку — перевір, чи бібліотека вже це робить:

- Структурований output → `with_structured_output(SchemaModel)`, не ручний JSON parsing.
- Chunking → `RecursiveCharacterTextSplitter`, не власна логіка розбиття.
- Hybrid retrieval → `EnsembleRetriever` з LangChain, не ручний RRF (якщо API підходить).
- Tool definition → `@tool` декоратор, не ручні JSON schemas.
- Memory → `PostgresSaver` (LangGraph checkpointer), не власна serialization логіка.
- Tracing → Langfuse `CallbackHandler`, не ручне логування.
- HITL → `HumanInTheLoopMiddleware` (LangGraph), не власні interrupt-механізми.

Власний код пишемо тільки коли бібліотека не покриває кейс — і документуємо причину в docstring модуля.

---

## 3. Структура модулів

```
procurement-support/
├── main.py                        # Entry point: Slack listener + REPL fallback
├── supervisor.py                  # LangGraph definition + Supervisor logic
│
├── agents/
│   ├── __init__.py
│   ├── planner.py                 # Planner agent (returns ResearchPlan)
│   ├── lawyer.py                  # Lawyer agent (RAG-only, laws collection)
│   ├── common_support.py          # Common support (RAG + web)
│   ├── technical_support.py       # Technical support (RAG + web with whitelist)
│   ├── critic.py                  # Critic agent (CritiqueResult)
│   └── escalation.py              # Escalation agent (Slack + report)
│
├── tools/
│   ├── __init__.py
│   ├── rag.py                     # RAG tool: hybrid search wrapper for agents
│   ├── web_search.py              # Tavily wrapper з UA-фільтром і domain whitelist
│   └── slack_publisher.py         # Slack message publishing
│
├── retrieval/
│   ├── __init__.py
│   ├── retriever.py               # Hybrid search (semantic + BM25 + RRF + rerank)
│   ├── reranker.py                # Cross-encoder reranking logic
│   └── embeddings.py              # Embedding model wrapper
│
├── ingest/
│   ├── __init__.py
│   ├── pipeline.py                # Ingestion orchestrator
│   ├── chunkers.py                # Strategy per collection (laws / articles)
│   └── run_ingest.py              # CLI entrypoint: python -m ingest.run_ingest
│
├── schemas.py                     # Pydantic models (всі контракти)
├── final_response.py              # Aggregator: workers → user-facing response
├── language.py                    # Language detection + section labels mapping
│
├── config.py                      # Pydantic Settings — всі .env vars
├── prompts/                       # Backup промптів (live версія в Langfuse)
│   ├── planner.md
│   ├── lawyer.md
│   ├── common_support.md
│   ├── technical_support.md
│   └── critic.md
│
├── observability/
│   ├── __init__.py
│   ├── langfuse_client.py         # Langfuse setup, prompt loading helpers
│   └── callbacks.py               # CallbackHandler config
│
├── tests/
│   ├── golden_dataset.json
│   ├── conftest.py
│   ├── test_planner.py
│   ├── test_lawyer.py
│   ├── test_common_support.py
│   ├── test_technical_support.py
│   ├── test_critic.py
│   ├── test_escalation.py
│   ├── test_tools.py              # Tool correctness
│   └── test_e2e.py
│
├── data/                          # Source documents для ingestion (JSONL)
│   ├── laws/
│   └── articles/
│
├── output/                        # Escalation reports (audit trail)
│
├── requirements.txt
├── .env.example
├── README.md
├── ARCHITECTURE.md                # цей файл
└── DELIVERY_CHECKLIST.md
```

**Принципи розкладки:**
- `agents/` — кожен агент — окремий модуль, що експортує `build_agent()` фабрику.
- `tools/` — функції-обгортки, які агенти викликають як tools (через `@tool` декоратор LangChain).
- `retrieval/` — низькорівнева логіка пошуку, не залежить від агентів. Tools з `tools/rag.py` викликають це.
- `ingest/` — окремий пайплайн, не імпортується з runtime коду.
- `schemas.py` — single source of truth для всіх Pydantic-контрактів.

---

## 4. Контракти між агентами (Pydantic схеми)

Усі inter-agent комунікації — через Pydantic-моделі. Жодних "сирих рядків" між агентами.

### 4.1 ResearchPlan (Planner → Supervisor)

```python
class SubTask(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    query: str
    rationale: str

class ResearchPlan(BaseModel):
    is_on_topic: bool
    off_topic_reason: str | None = None
    language: Literal["uk", "en"]
    original_query: str
    subtasks: list[SubTask] = Field(default_factory=list)
    needs_human: bool = False
    escalation_reason: str | None = None

    @model_validator(mode="after")
    def validate_consistency(self):
        # if not is_on_topic → subtasks must be empty
        # if needs_human → escalation_reason must be set
        # if is_on_topic and not needs_human → subtasks must be non-empty
        ...
```

### 4.2 WorkerResponse (Worker → Supervisor)

```python
class WorkerResponse(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    found: bool
    answer: str | None = None
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False                    # тільки technical_support
    needs_human_reason: str | None = None

class Source(BaseModel):
    title: str                                   # human-readable (breadcrumb або title)
    url: str | None
    doc_id: str                                  # для дедуплікації
    metadata: dict                               # version_date, date_published тощо
```

### 4.3 CritiqueResult (Critic → Supervisor)

```python
class RevisionRequest(BaseModel):
    topic: Literal["legal", "procurement_general", "technical_system"]
    request: str                                 # що саме переробити
    severity: Literal["minor", "major"]

class CritiqueResult(BaseModel):
    verdict: Literal["approve", "revise"]
    freshness_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    structure_score: float = Field(ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)
    revision_requests: list[RevisionRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_revisions(self):
        # if verdict == "revise" → revision_requests must be non-empty
        ...
```

### 4.4 EscalationOutput (Escalation → Slack/File)

```python
class EscalationOutput(BaseModel):
    summary: str
    category: Literal["bug", "feature_request", "unanswerable", "max_retries_exceeded"]
    customer_message: str                        # оригінальний запит
    attempted_resolution: str                    # що система намагалась зробити
    full_context: dict                           # plan + worker responses + critic history
    timestamp: datetime
    session_id: str
```

### 4.5 GraphState (LangGraph state)

Загальний state, який передається між nodes у LangGraph:

```python
class GraphState(TypedDict):
    # Input
    user_message: str
    session_id: str
    user_id: str

    # Planner output
    plan: ResearchPlan | None

    # Worker outputs (зібрані через reducer)
    worker_responses: Annotated[list[WorkerResponse], operator.add]

    # Critic loop state
    critic_history: list[CritiqueResult]
    retry_count: int

    # Final
    aggregated_response: str | None
    escalated: bool
    final_response: str | None
```

---

## 5. LangGraph: nodes, edges, control flow

### 5.1 Граф

```
START
  │
  ▼
[planner_node]
  │
  ├─ if not is_on_topic ──────► [off_topic_response_node] ──► END
  ├─ if needs_human ──────────► [escalation_node] ──────────► END
  │
  ▼
[fan_out_dispatcher]
  │
  ├──► [lawyer_node]              ┐
  ├──► [common_support_node]      ├─ паралельно (Send API)
  └──► [technical_support_node]   ┘
  │
  ▼
[aggregate_responses_node]
  │
  ▼
[critic_node]
  │
  ├─ if approve ─────────────────► [final_response_node] ──► END
  ├─ if revise && retries < N ──► [targeted_redispatcher] ─► (повторно ті ж workers)
  └─ if retries >= N ────────────► [escalation_node] ──────► END
```

### 5.2 Nodes — відповідальності

| Node | Input | Output | LLM-виклик? |
|---|---|---|---|
| `planner_node` | `user_message`, `session_id` | `plan: ResearchPlan` | Так (structured output) |
| `off_topic_response_node` | `plan.off_topic_reason` | `final_response` (статичний шаблон) | Ні |
| `fan_out_dispatcher` | `plan.subtasks` | `Send` команди до workers | Ні (logic) |
| `lawyer_node` | `SubTask` | `WorkerResponse` | Так (з RAG context) |
| `common_support_node` | `SubTask` | `WorkerResponse` | Так (з RAG + web context) |
| `technical_support_node` | `SubTask` | `WorkerResponse` | Так (з RAG + web context) |
| `aggregate_responses_node` | `worker_responses` | `aggregated_response` (markdown sections) | Ні (logic) |
| `critic_node` | `aggregated_response`, `plan` | `CritiqueResult` | Так (structured output) |
| `targeted_redispatcher` | `revision_requests` | `Send` команди до targeted workers | Ні (logic) |
| `escalation_node` | весь state | `EscalationOutput` + Slack post + file | Так (для summary) |
| `final_response_node` | `aggregated_response` | `final_response` | Ні |

### 5.3 Conditional edges

```python
# from planner_node
def route_after_planner(state: GraphState) -> str:
    if not state["plan"].is_on_topic:
        return "off_topic_response_node"
    if state["plan"].needs_human:
        return "escalation_node"
    return "fan_out_dispatcher"

# from critic_node
def route_after_critic(state: GraphState) -> str:
    last_critique = state["critic_history"][-1]
    if last_critique.verdict == "approve":
        return "final_response_node"
    if state["retry_count"] >= settings.CRITIC_MAX_RETRIES:
        return "escalation_node"
    return "targeted_redispatcher"
```

### 5.4 Fan-out через Send API

Динамічний fan-out за списком підзадач:

```python
def fan_out_dispatcher(state: GraphState) -> list[Send]:
    return [
        Send(node_for_topic(subtask.topic), {"subtask": subtask, "session_id": state["session_id"]})
        for subtask in state["plan"].subtasks
    ]

def node_for_topic(topic: str) -> str:
    return {
        "legal": "lawyer_node",
        "procurement_general": "common_support_node",
        "technical_system": "technical_support_node",
    }[topic]
```

`worker_responses` у state використовує `operator.add` як reducer — кожен worker додає свою відповідь до списку.

### 5.5 Targeted re-dispatch (Critic loop)

При `revise` Supervisor запускає **тільки** тих workers, до кого є `revision_requests`. Інші відповіді з попереднього раунду переносяться як є.

```python
def targeted_redispatcher(state: GraphState) -> list[Send]:
    last_critique = state["critic_history"][-1]
    return [
        Send(
            node_for_topic(req.topic),
            {
                "subtask": find_subtask(state["plan"], req.topic),
                "revision_feedback": req.request,
                "session_id": state["session_id"],
            }
        )
        for req in last_critique.revision_requests
    ]
```

Worker-агенти приймають опційний `revision_feedback` параметр, який інжектується у prompt: *"Попередня версія відповіді отримала зауваження: ... Перероби."*

---

## 6. RAG підсистема

### 6.1 Архітектура retrieval

```
Agent.search(query, collection, filters)
  │
  ▼
retrieval/retriever.py :: hybrid_search()
  │
  ├──► retrieval/embeddings.py → embed query
  ├──► Qdrant.search(vector, filters, top=20)         ┐
  ├──► rank_bm25 (in-memory) → top 20                 ├─ Ensemble (RRF)
  ├──► merge with weights (0.6 / 0.4)                 ┘
  ├──► retrieval/reranker.py → cross-encoder rerank → top 5
  ├──► filter by RERANK_SCORE_THRESHOLD
  ▼
list[Chunk]  ──►  Agent context
```

### 6.2 BM25 індекс — стратегія

BM25 потребує in-memory корпусу. Два варіанти:
- **MVP:** на старті завантажуємо весь корпус кожної колекції в память, тримаємо `BM25Okapi` instance як singleton.
- **Production:** Qdrant 1.10+ має нативний BM25 support через sparse vectors. Якщо встигнемо — переходимо.

Для курсової — MVP-варіант ОК (датасети не гігантські).

### 6.3 Інтерфейс retriever

```python
class Chunk(BaseModel):
    id: str
    doc_id: str
    text: str
    metadata: dict
    score: float                    # final score after reranking

def hybrid_search(
    query: str,
    collection: Literal["laws", "articles"],
    filters: dict | None = None,    # Qdrant payload filter
    top_k: int = 5,
) -> list[Chunk]:
    ...
```

### 6.4 Pre-filtering за метаданими

**Lawyer Agent** перед vector search детектить номер статті в запиті (regex `\d+(-\d+)?`) і додає filter:

```python
filters = {"must": [{"key": "article_number", "match": {"value": "164-14"}}]}
```

**Technical Support Agent** додає filter за whitelist тегів:

```python
filters = {"must": [{"key": "tags", "match": {"any": settings.TECH_SUPPORT_TAG_WHITELIST}}]}
```

### 6.5 Ingestion pipeline

```
JSONL files (data/laws/*.jsonl, data/articles/*.jsonl)
  │
  ▼
ingest/pipeline.py
  │
  ├──► chunker_for_collection(collection)      # окрема стратегія для laws / articles
  ├──► build embedding text:
  │     - laws:     breadcrumb + section_heading + text
  │     - articles: title + tags(joined) + text
  ├──► embed batch (OpenAI)
  ├──► Qdrant.upsert(collection, points)
  ▼
[completion + stats: docs ingested, chunks created]
```

**Запуск:** `python -m ingest.run_ingest --collection=laws|articles|all`.

**Idempotency:** `id` chunk-а — детермінований (хеш від `doc_id + chunk_index`). Re-ingest перезаписує без дублювання.

---

## 7. Web Search підсистема

### 7.1 Шари

```
Agent.web_search(query, allowed_domains=None)
  │
  ▼
tools/web_search.py
  │
  ├──► Tavily API call (language=uk, country=UA, include_domains=allowed_domains)
  ├──► language detection per result (langdetect)
  ├──► drop non-UA results
  ├──► trim snippets to N chars
  ▼
list[SearchResult]
```

### 7.2 Стратегії для агентів

| Агент | `allowed_domains` |
|---|---|
| Common Support | `None` (без обмежень) |
| Technical Support | `settings.TECH_SUPPORT_ALLOWED_DOMAINS` |
| Critic (опційно) | `None` |

### 7.3 Technical Support — інструменти пошуку

**Technical Support Agent** має чотири джерела знань (в порядку пріоритету):

| Інструмент | Джерело | Умова активації |
|---|---|---|
| `confluence_search(query)` | Confluence Cloud CQL search | Завжди прив'язаний; перевіряє `CONFLUENCE_URL` + `CONFLUENCE_API_TOKEN` при першому виклику; опційно обмежується просторами `CONFLUENCE_SPACE_KEYS` |
| `rag_search_articles(query)` | Qdrant `articles` collection (гібридний пошук) | Завжди; pre-filter по `tags` ∈ `TECH_SUPPORT_TAG_WHITELIST` |
| `github_repo_search(query)` | GitHub REST Search API, code search | Тільки якщо `TECH_SUPPORT_GITHUB_REPOS` не порожній; обмежений `repo:owner/name` кваліфікаторами; опційно автентифікований через `GITHUB_API_TOKEN` |
| `web_search_technical(query)` | Tavily, обмежений хостами | Завжди; хости зі `TECH_SUPPORT_ALLOWED_DOMAINS` (лише bare hostnames — без схем і шляхів) |

---

## 8. Sessions та память

### 8.1 LangGraph Checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(settings.POSTGRES_URL)
graph = workflow.compile(checkpointer=checkpointer)
```

### 8.2 Session ID

Формується в `main.py`:

```python
def make_session_id(slack_event) -> str:
    return f"{slack_event.team_id}:{slack_event.channel_id}:{slack_event.user_id}"
```

Передається в LangGraph як `config={"configurable": {"thread_id": session_id}}`.

### 8.3 TTL

Окремий лайтвейт-cleanup (cron / scheduled job у main loop) видаляє checkpoints старше `SESSION_TTL_HOURS`. Не критично для MVP, можна зробити в кінці.

---

## 9. Slack інтеграція

### 9.1 Архітектура

```
Slack Events API
  │
  ▼
main.py :: SlackBolt app
  │
  ├──► message handler (user channel) ──► invoke graph ──► reply with final_response
  ├──► escalation publisher ──► post to expert channel
  ▼
slack-sdk
```

### 9.2 Канали

- **User channel** (`SLACK_USER_CHANNEL_ID`) — bot слухає `app_mention` і `message.channels` events. Відповідає в thread.
- **Expert channel** (`SLACK_EXPERT_CHANNEL_ID`) — bot **тільки публікує** (escalation messages). Не слухає.

### 9.3 Message формат

User channel — простий markdown відповідь з секціями.

Expert channel — структуроване повідомлення (Block Kit або markdown):

```
🚨 Escalation: {category}
*Session:* {session_id}
*Original query:* {customer_message}

*Plan:*
{plan summary}

*What system tried:*
{attempted_resolution}

*Critic feedback (if applicable):*
{critic gaps}

*Suggested next steps:*
{from EscalationOutput}
```

---

## 10. Observability (Langfuse)

### 10.1 Інтеграція

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_BASE_URL,
)

graph.invoke(
    initial_state,
    config={
        "configurable": {"thread_id": session_id},
        "callbacks": [langfuse_handler],
        "metadata": {
            "user_id": user_id,
            "session_id": session_id,
            "tags": ["procurement-support"],
        },
    },
)
```

### 10.2 Prompt Management

Усі system prompts завантажуються з Langfuse:

```python
from langfuse import Langfuse

langfuse = Langfuse(...)

def load_prompt(name: str, label: str = "production", **vars) -> str:
    prompt = langfuse.get_prompt(name, label=label)
    return prompt.compile(**vars)
```

Prompts в Langfuse:
- `procurement-planner`
- `procurement-lawyer`
- `procurement-common-support`
- `procurement-technical-support`
- `procurement-critic`
- `procurement-escalation`

Локальний backup в `prompts/*.md` — для dev fallback (якщо Langfuse недоступний при старті) і для review/diff у git.

### 10.3 LLM-as-a-Judge evaluators

Налаштовуються в Langfuse UI (не в коді):
- **Groundedness** — для відповідей workers (input + retrieval context + output).
- **Off-topic adherence** — для перевірки доменних обмежень.
- (опційно) **Source citation quality** — чи в `final_response` є посилання на джерела.

---

## 11. Конфігурація (Pydantic Settings)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # LLM
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"

    # GitHub search (optional; bound to Technical Support when non-empty)
    github_api_token: str | None = None
    tech_support_github_repos: list[str] = []  # CSV-parsed; owner/repo strings

    # Web search (Tavily)
    tavily_api_key: str
    tech_support_allowed_domains: list[str] = []  # CSV-parsed; bare hostnames only
    tech_support_tag_whitelist: list[str] = []

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str | None = None
    qdrant_laws_collection: str = "laws"
    qdrant_articles_collection: str = "articles"
    laws_freshness_threshold_days: int = 180
    articles_freshness_threshold_days: int = 365

    # Hybrid retrieval
    retrieval_top_k: int = 20
    hybrid_semantic_weight: float = 0.6
    hybrid_bm25_weight: float = 0.4

    # Reranking
    reranker_model: str = "BAAI/bge-reranker-base"
    rerank_top_k: int = 5
    rerank_score_threshold: float = 0.3

    # Postgres
    postgres_url: str
    session_ttl_hours: int = 24

    # Slack
    slack_bot_token: str
    slack_signing_secret: str
    slack_user_channel_id: str
    slack_expert_channel_id: str

    # Agent behavior
    critic_max_retries: int = 3
    worker_timeout_seconds: int = 60
    planner_max_subtasks: int = 3

    # Observability
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_base_url: str = "https://us.cloud.langfuse.com"

settings = Settings()
```

---

## 12. Error handling та resilience

### 12.1 Принципи

- **Graceful degradation:** падіння одного worker (timeout, exception) не валить весь pipeline. Worker повертає `WorkerResponse(found=False, ...)` і Critic / Aggregator вміють це обробити.
- **Retry на рівні агентів:** Critic loop — це і є retry-механізм для якісних проблем. Технічні retry (network timeout) — на рівні tools (через `tenacity`).
- **Hard limits:** `CRITIC_MAX_RETRIES`, `WORKER_TIMEOUT_SECONDS`, `PLANNER_MAX_SUBTASKS` — все з `.env`.

### 12.2 Failure modes і реакції

| Failure | Реакція |
|---|---|
| Tavily API down | Worker повертає `found=False`, Critic може ескалювати або approve без web sources |
| Qdrant unavailable | Worker повертає `found=False, needs_human=True` → ескалація |
| LLM timeout / rate limit | Tenacity retry (3 спроби з backoff) → якщо все падає, ескалація з технічною помилкою |
| Pydantic validation failure (LLM повернув погану структуру) | Один retry з error в prompt → якщо знову fail, ескалація |
| Slack publish failure | Логуємо в Langfuse, escalation report зберігається у файл як fallback |

---

## 13. Testing strategy

### 13.1 Шари тестування

| Шар | Інструмент | Що тестується |
|---|---|---|
| Unit | pytest | Чисті функції (chunkers, language detection, RRF merge, score parsing) |
| Component | DeepEval | Поведінка кожного агента ізольовано |
| Integration | pytest + mocks | Граф з мокнутими LLM/tools — control flow |
| E2E | DeepEval | Повний pipeline на golden dataset |

### 13.2 Golden dataset

Структура:
```json
{
  "id": "happy-001",
  "category": "happy_path",
  "input": "Compare procurement procedures: open tender vs simplified procurement",
  "language": "uk",
  "expected_topics": ["procurement_general", "legal"],
  "expected_output": "...",
  "expected_sources_doc_ids": ["..."],
  "should_escalate": false
}
```

15-20 прикладів: 5 happy path, 5 edge cases, 5 failure (off-topic, escalation, multi-topic).

### 13.3 Метрики

- **GEval Plan Quality** — Planner.
- **Groundedness** — workers.
- **Critique Quality** (custom GEval) — Critic.
- **Tool Correctness** — який agent що викликає.
- **Answer Relevancy** — e2e.
- **Correctness** (vs expected_output) — e2e.

---

## 14. Deployment / запуск

### 14.1 Локальний dev

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# fill in keys

# 3. Start infrastructure
docker compose up -d  # Qdrant + Postgres

# 4. Ingest data
python -m ingest.run_ingest --collection=all

# 5. Sync prompts to Langfuse (one-time)
python scripts/sync_prompts.py

# 6. Run
python main.py
```

### 14.2 Docker compose (infrastructure only)

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["./qdrant_data:/qdrant/storage"]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: agent_sessions
    ports: ["5432:5432"]
    volumes: ["./pg_data:/var/lib/postgresql/data"]
```

Сам додаток запускається поза Docker — для зручного hot-reload в розробці.

---

## 15. Архітектурні рішення (ADR-стиль, коротко)

| # | Рішення | Альтернативи | Чому так |
|---|---|---|---|
| 1 | Orchestrator-Workers + Evaluator-Optimizer | Простий Routing | Multi-topic запити реальні в домені; Critic loop підвищує якість |
| 2 | LangGraph замість custom state machine | Custom + Pydantic | Готовий checkpointer, fan-out, conditional edges, інтеграція з Langfuse |
| 3 | Qdrant замість pgvector | pgvector (один сервіс з Postgres) | Кращий payload filtering, швидший на гібридних навантаженнях |
| 4 | Hybrid (semantic + BM25) + reranking | Тільки semantic | Юридичний домен має багато точних термінів і номерів — BM25 critical |
| 5 | Окрема колекція `laws` від `articles` | Одна колекція з типом у метаданих | Різні стратегії chunking, різний embedding text, чіткіше розділення прав агентів |
| 6 | Planner може напряму ескалювати | Завжди через workers | Економія на очевидних bug reports / feature requests |
| 7 | Targeted re-dispatch при revise | Перезапуск всіх workers | Економія токенів і часу |
| 8 | Section-based aggregation | LLM-aggregator | Дешевше, передбачуваніше, легше тестувати |
| 9 | Static off-topic / escalation messages | LLM-генеровані | Передбачувана UX, без ризику галюцинацій на критичних шляхах |
| 10 | Langfuse Prompt Mgmt | Захардкожені prompts | A/B тестування, версіонування, switching без redeploy |
| 11 | Library-first development | Власна реалізація для контролю | Менше підтримки, кращий fit з ecosystem'ом, швидше до результату; стек обрано саме за повноту фіч |
| 12 | Confluence Cloud як третє джерело знань для Technical Support | Інгестація сторінок Confluence у колекцію `articles` Qdrant | Live search зберігає актуальність без re-ingest; інгестація вимагала б окремого пайплайну синхронізації та ризикувала би застарілими даними. Інструмент env-gated — агент функціонує без Confluence credentials |
| 13 | GitHub Search API як окремий інструмент `github_repo_search` для репозиторіїв | Tavily `include_domains` з repo-path рядками | Tavily domain filtering — хост-рівень, не repo-рівень; GitHub Code Search API надає точний пошук по коду й документації у визначеному списку репозиторіїв. `TECH_SUPPORT_ALLOWED_DOMAINS` — лише bare hostnames для Tavily. Інструмент env-gated через `TECH_SUPPORT_GITHUB_REPOS` — агент функціонує без GitHub credentials |