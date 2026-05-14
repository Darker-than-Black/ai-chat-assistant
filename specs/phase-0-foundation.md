# Plan: Phase 0 — Foundation

> Source roadmap: `docs/DELIVERY_CHECKLIST.md` Phase 0 (§§ 0.1–0.4)
> Source architecture: `docs/ARCHITECTURE.md` (§§ 2, 3, 11, 14.2)
> Project guidance: `CLAUDE.md`

## Task Description

Реалізувати **Phase 0 — Foundation** з `docs/DELIVERY_CHECKLIST.md`: підняти каркас репозиторію (директорії, залежності, конфіг, інфраструктура, заглушка `main.py`) так, щоб виконувалося формальне визначення кінця фази:

> **Кінець фази:** проєкт запускається з `python main.py` і виводить `Hello`.

Це vertical-slice "нульового" рівня — ще немає агентів, RAG чи граф-логіки, але вся фундаментальна обв'язка (структура, залежності, налаштування, локальна інфраструктура) має бути на місці і пройти валідацію, щоб Phase 1 міг будуватись поверх неї без блокерів.

## Objective

По завершенні плану в репо є:

1. Канонічна директорна структура з `ARCHITECTURE.md § 3` (порожні `agents/`, `tools/`, `retrieval/`, `ingest/`, `observability/`, `prompts/`, `tests/`, `output/` — тільки `__init__.py` де потрібно).
2. Робочий `requirements.txt` з повним стеком фази (LangChain/LangGraph, Qdrant, Postgres checkpointer, Slack, Tavily, Langfuse, deepeval, pytest, langdetect, tenacity, sentence-transformers, rank_bm25), який встановлюється чисто у свіжому venv.
3. `config.py` з повним `Settings(BaseSettings)` згідно `ARCHITECTURE § 11`, з валідаторами CSV-полів, `SecretStr` для секретів, та з `.env.example` що містить всі ключі з коментарями.
4. `docker-compose.yml` що піднімає Qdrant + Postgres (runtime інфра); існуюча MariaDB-композиція для пайплайну ingestion переноситься в `docker-compose.ingest.yml`.
5. Скрипт ініціалізації схеми Postgres-чекпоінтера LangGraph (через `PostgresSaver.setup()`).
6. Заглушка `main.py`, яка завантажує `Settings`, друкує `Hello` і запускає простий echo-REPL до EOF/`exit`.
7. `.gitignore` з усіма необхідними виключеннями (Python, venv, env, runtime data, IDE, OS).
8. README — стиснутий до Phase-0 заглушки з посиланнями на `docs/ARCHITECTURE.md` та `docs/DELIVERY_CHECKLIST.md` (поточні 36 КБ архітектурного контенту вже мігровано в `docs/ARCHITECTURE.md`).
9. Оновлений `CLAUDE.md` (notes про шлях стейка, який вже не діє: розділ root-stubs → directories).

Після виконання — всі перевірки з розділу **Validation Commands** проходять.

## Problem Statement

Поточний стан репозиторію — Apr-16 scaffold плюс розрізнено доданий код пайплайнів збору даних. Це створює три блокери для Phase 1+:

1. **Структурне неспівпадіння**: код розкладений як root-level `agent.py`/`ingest.py`/`retriever.py`/`tools.py` (порожні стаби), але `docs/ARCHITECTURE.md § 3` фіксує канонічну розкладку як піддиректорії (`agents/`, `ingest/`, `retrieval/`, `tools/`). Phase 1 (наприклад `agents/lawyer.py`) не зможе чисто додаватись, якщо root-стаби не прибрані.
2. **Конфіг занадто вузький**: `config.py` має ~10 полів (api_key, model_name, chunk_*, retrieval_top_k…). У `ARCHITECTURE § 11` визначено ~30 полів (Tavily, Qdrant, Postgres, Slack, Langfuse, behavior limits, freshness thresholds). Без розширення Settings агенти не матимуть звідки читати keys, а введення `os.environ.get(...)` поза `config.py` порушить Convention з `CLAUDE.md`.
3. **Інфраструктура неповна**: `docker-compose.yml` має тільки MariaDB (для скрипта `scripts/export_infobox_db.py`), немає Qdrant і Postgres, що блокує сесії (`PostgresSaver`) і RAG (Qdrant-колекції) у наступних фазах.

Phase 0 закриває ці три блокери одним прохідним cleanup-ом ще до того, як з'явиться змістовна логіка.

## Solution Approach

Підхід — **scaffold-only**, без бізнес-логіки. Зміни роблять каркас канонічним згідно `ARCHITECTURE.md`. Жодних LLM-викликів, жодного імпорту LangChain/LangGraph під час `python main.py` — лише `Settings` + REPL. Це гарантує що Phase 0 проходить без zaшумлених залежностей (наприклад, OPENAI_API_KEY ще може бути порожнім — settings його не викличе).

### Architecture Decisions

- **Affected graph nodes**: жодних. Phase 0 не торкається графа — жодного вузла ще не існує.
- **Schemas**: жодних змін у `schemas.py`. Файл буде створений у Phase 1.1, а не тут.
- **RAG collection(s)**: жодних — колекції Qdrant створюються у Phase 1.2.
- **External calls**: жодних рантаймових. Локальна інфра (`docker-compose.yml`) — Qdrant і Postgres. Існуючий `docker-compose.yml` (MariaDB) переноситься в `docker-compose.ingest.yml`, бо ця БД потрібна тільки скрипту `scripts/export_infobox_db.py` (data-pipeline, не runtime).
- **Sessions / persistence**: формат і session-ключ не визначаються тут — буде Phase 5. Але інфраструктура (Postgres + LangGraph checkpointer schema) має бути готова: в Phase 0 створюємо БД-сервіс і запускаємо `PostgresSaver.setup()` через окремий one-shot скрипт `scripts/setup_postgres_checkpointer.py`. Сам `PostgresSaver` ще не використовується.
- **Prompt source**: жодних промптів у Phase 0. `prompts/` створюється як порожня директорія для майбутніх Phase 1+ backup-копій (live-версія в Langfuse — Phase 7).
- **Деструктивні зміни** (потребують підтвердження користувача): видалення `agent.py`, `ingest.py`, `retriever.py`, `tools.py` (4 root-стаби, всі порожні / TODO-only), радикальне скорочення `README.md` (з 36 КБ до ~3 КБ). Зміст README не втрачається — повний документ дублюється у `docs/ARCHITECTURE.md`.

## Relevant Files

Існуючі файли, що **читаються або змінюються** у цій фазі:

- `docs/ARCHITECTURE.md` — джерело структури, технологій і Settings-схеми (§§ 2, 3, 11, 14.2). **Не редагуємо.**
- `docs/DELIVERY_CHECKLIST.md` — джерело Phase-0 чек-листа. **Не редагуємо тут**, але після завершення відмічаємо `[x]` (окремий commit).
- `CLAUDE.md` — оновлюємо опис root-стабів (бо ми їх видаляємо) і список common commands (новий `docker-compose.yml`).
- `README.md` — стискаємо до Phase-0 заглушки. (Контент вже представлений у `docs/ARCHITECTURE.md`.)
- `config.py` — повне розширення `Settings` згідно `ARCHITECTURE § 11`.
- `requirements.txt` — повна заміна списку пакетів згідно `ARCHITECTURE § 2`.
- `docker-compose.yml` — переписується для Qdrant + Postgres. Поточний вміст (MariaDB) переїжджає в `docker-compose.ingest.yml`.
- `main.py` — повне переписування у Phase-0 заглушку (settings + echo REPL, **без** імпорту `agent`).
- `agent.py`, `ingest.py`, `retriever.py`, `tools.py` — **видаляються** (root-стаби, конфліктують з канонічною структурою піддиректорій).

### New Files

- `.gitignore` — Python, venv, env (крім `.env.example`), runtime data (`qdrant_data/`, `pg_data/`, `output/`, `index/`), `__pycache__`, IDE (`.idea/`), OS (`.DS_Store`).
- `.env.example` — повний перелік ключів з `ARCHITECTURE § 11` з коментарями. Без значень для секретів (тільки заглушки).
- `docker-compose.ingest.yml` — переїзд існуючої MariaDB-композиції; запускається як `docker compose -f docker-compose.ingest.yml up -d`.
- `scripts/setup_postgres_checkpointer.py` — one-shot CLI: читає `settings.postgres_url`, створює `PostgresSaver`, викликає `.setup()`.
- `agents/__init__.py` — порожній (placeholder для Phase 1.6+).
- `tools/__init__.py` — порожній (placeholder для Phase 1.5+).
- `retrieval/__init__.py` — порожній (placeholder для Phase 1.2+).
- `ingest/__init__.py` — порожній (placeholder для Phase 1.3+).
- `observability/__init__.py` — порожній (placeholder для Phase 7).
- `prompts/.gitkeep` — placeholder директорії для Phase 1.6+ backup-промптів.
- `tests/__init__.py` — порожній (placeholder для Phase 1.1+ unit tests).
- `output/.gitkeep` — placeholder директорії для Phase 6 escalation reports (директорія в `.gitignore`, тільки `.gitkeep` коммітимо).

### Файли НЕ змінюються у Phase 0

- `data/law/*`, `data/infobox/*` — дані вже згенеровані попередніми скриптами; ingestion буде у Phase 1.3.
- `scripts/create_procurement_law_dataset.py`, `scripts/export_infobox_db.py` — data-pipeline працює, не чіпаємо.
- `prozorro_backup.sql` — відсутній у репо (за CLAUDE.md), залишається обовʼязком користувача для ingest-пайплайну.

## Implementation Phases

- [ ] **Phase 1: Repository scaffolding (Checklist 0.1)** — структура директорій, `.gitignore`, README-stub, видалення root-стабів.
  - Status:
  - Comments:

- [ ] **Phase 2: Dependencies (Checklist 0.1)** — переписати `requirements.txt`, перевірити чисту установку у свіжому venv.
  - Status:
  - Comments:

- [ ] **Phase 3: Configuration (Checklist 0.2)** — розширити `Settings`, додати валідатори CSV-полів, написати `.env.example`, перевірити імпорт.
  - Status:
  - Comments:

- [ ] **Phase 4: Local infrastructure (Checklist 0.3)** — split `docker-compose.yml`, healthcheck Qdrant, скрипт `setup_postgres_checkpointer.py`.
  - Status:
  - Comments:

- [ ] **Phase 5: Stub main.py (Checklist 0.4)** — переписати `main.py` на settings + echo REPL з `Hello` greeting.
  - Status:
  - Comments:

- [ ] **Phase 6: Validation & cleanup** — прогнати всі validation commands, оновити CLAUDE.md, поставити `[x]` у DELIVERY_CHECKLIST, commit з префіксом `[0.x]`.
  - Status:
  - Comments:

## Step by Step Tasks

### 1. Repository scaffolding (Checklist 0.1)

- [ ] **Створити канонічні директорії з ARCHITECTURE § 3** — `mkdir -p agents tools retrieval ingest observability prompts tests output`. (Існуючі `data/`, `scripts/`, `docs/` залишаються.)
  - Status:
  - Comments:

- [ ] **Додати `__init__.py`-файли в Python-пакети** — порожні файли в `agents/`, `tools/`, `retrieval/`, `ingest/`, `observability/`, `tests/`. (`prompts/` і `output/` — не Python-пакети, для них `.gitkeep`.)
  - Status:
  - Comments:

- [ ] **Видалити root-стаби (`agent.py`, `ingest.py`, `retriever.py`, `tools.py`)** — конфліктують з директоріями з тими ж іменами. Усі чотири — порожні (`...` / `pass` / TODO-доковки), безпечно видаляти. **Перед видаленням переконатись що `git status` не показує uncommitted changes у цих файлах.**
  - Status:
  - Comments:

- [ ] **Створити `.gitignore`** — стандартний Python (`__pycache__/`, `*.pyc`, `*.pyo`, `*.egg-info/`, `build/`, `dist/`), venv (`.venv/`, `venv/`, `env/`), env-секрети (`.env` — але **не** `.env.example`), runtime data (`qdrant_data/`, `pg_data/`, `output/`, `index/`, `*.faiss`), IDE (`.idea/`, `.vscode/`), OS (`.DS_Store`, `Thumbs.db`), tooling caches (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`).
  - Status:
  - Comments:

- [ ] **Переписати `README.md` як Phase-0 заглушку** — структура: (1) одна-абзац опис проєкту з акцентом на трьох доменах; (2) ASCII-діаграма архітектури з `CLAUDE.md` (Supervisor → Planner → workers → Critic → Escalation); (3) "Detailed design — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)"; (4) "Implementation roadmap — see [docs/DELIVERY_CHECKLIST.md](docs/DELIVERY_CHECKLIST.md)"; (5) одна-секція Quick Start з placeholder "Filled in Phase 9.1". Розмір ≤ 100 рядків. **Втрачуваний контент уже продубльований у `docs/ARCHITECTURE.md` — без втрати інформації.**
  - Status:
  - Comments:

- [ ] **Створити `prompts/.gitkeep` і `output/.gitkeep`** — щоб директорії існували в git, але вміст не комітився.
  - Status:
  - Comments:

### 2. Dependencies (Checklist 0.1)

- [ ] **Переписати `requirements.txt` згідно `ARCHITECTURE § 2`** — повний перелік:
    ```
    # Core framework
    langchain>=1.2.0
    langchain-core>=1.2.0
    langchain-classic>=1.0
    langchain-community>=0.4
    langchain-openai>=0.4
    langchain-anthropic>=0.4
    langgraph>=0.6
    langgraph-checkpoint-postgres>=2.0

    # Configuration & contracts
    pydantic>=2.12.0
    pydantic-settings>=2.12.0

    # Vector DB
    qdrant-client>=1.13

    # Hybrid retrieval
    rank_bm25>=0.2.2
    sentence-transformers>=3.0

    # Web search
    tavily-python>=0.5
    langdetect>=1.0.9

    # Slack
    slack-sdk>=3.30
    slack-bolt>=1.20

    # Observability
    langfuse>=2.50

    # Resilience
    tenacity>=9.0

    # Postgres driver (для PostgresSaver)
    psycopg[binary]>=3.2

    # Testing
    pytest>=8.0
    deepeval>=2.0
    ```
    - Видалені пакети: `faiss-cpu` (vector DB → Qdrant), `ddgs` (web search → Tavily), `trafilatura` (поза `ARCHITECTURE § 2`; додати назад якщо знадобиться `read_url` tool).
  - Status:
  - Comments:

- [ ] **Перевірити чисту установку** — `python -m venv /tmp/phase0-venv && source /tmp/phase0-venv/bin/activate && pip install -r requirements.txt && deactivate && rm -rf /tmp/phase0-venv`. Якщо є конфлікти resolver-а (наприклад langchain ↔ langchain-classic) — зафіксувати точніші пінг'и.
  - Status:
  - Comments:

### 3. Configuration (Checklist 0.2)

- [ ] **Переписати `config.py` згідно `ARCHITECTURE § 11`** — повний `Settings(BaseSettings)`:
    ```python
    from typing import Literal
    from pydantic import Field, SecretStr, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict


    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

        # LLM
        llm_provider: Literal["openai", "anthropic"] = "openai"
        llm_model: str = "gpt-4o"
        openai_api_key: SecretStr | None = None
        anthropic_api_key: SecretStr | None = None
        embedding_model: str = "text-embedding-3-small"

        # Web search
        tavily_api_key: SecretStr | None = None
        tech_support_allowed_domains: list[str] = Field(default_factory=list)
        tech_support_tag_whitelist: list[str] = Field(default_factory=list)

        # Qdrant
        qdrant_url: str = "http://localhost:6333"
        qdrant_api_key: SecretStr | None = None
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
        postgres_url: str = "postgresql://postgres:postgres@localhost:5432/agent_sessions"
        session_ttl_hours: int = 24

        # Slack
        slack_bot_token: SecretStr | None = None
        slack_signing_secret: SecretStr | None = None
        slack_user_channel_id: str | None = None
        slack_expert_channel_id: str | None = None

        # Agent behavior
        critic_max_retries: int = 3
        worker_timeout_seconds: int = 60
        planner_max_subtasks: int = 3

        # Observability
        langfuse_public_key: SecretStr | None = None
        langfuse_secret_key: SecretStr | None = None
        langfuse_base_url: str = "https://us.cloud.langfuse.com"

        @field_validator("tech_support_allowed_domains", "tech_support_tag_whitelist", mode="before")
        @classmethod
        def _split_csv(cls, v):
            if isinstance(v, str):
                return [item.strip() for item in v.split(",") if item.strip()]
            return v


    settings = Settings()
    ```
    - Phase-0 інваріант: усі секрети `Optional[SecretStr]`, з default `None`. Жоден агент ще не імпортується; settings має завантажуватись навіть коли в `.env` немає реальних ключів. Жорсткі вимоги стануть полями у Phase 1+ коли той чи інший компонент дійсно потрібен.
  - Status:
  - Comments:

- [ ] **Створити `.env.example`** — повний перелік ключів з коментарями-описами, в тому ж порядку що поля в `Settings`. Усі значення — заглушки (`changeme`, `xoxb-***`, тощо). Використати точні uppercase-імена що відповідають field-name'ам. Додати на початку коментар: `# Copy to .env and fill in real values; .env is git-ignored.`
  - Status:
  - Comments:

- [ ] **Smoke-тест імпорту** — `python -c "from config import settings; print(settings.llm_model)"` має надрукувати `gpt-4o` без помилки. Якщо `pydantic_settings` падає на missing required field — переконатись, що відповідне поле має `default` або `None`.
  - Status:
  - Comments:

### 4. Local infrastructure (Checklist 0.3)

- [ ] **Перейменувати існуючий `docker-compose.yml` → `docker-compose.ingest.yml`** — він обслуговує тільки `scripts/export_infobox_db.py`. Назва вказує на призначення.
  - Status:
  - Comments:

- [ ] **Створити новий `docker-compose.yml` (Qdrant + Postgres) згідно `ARCHITECTURE § 14.2`** —
    ```yaml
    services:
      qdrant:
        image: qdrant/qdrant:latest
        container_name: procurement-qdrant
        restart: unless-stopped
        ports:
          - "6333:6333"
          - "6334:6334"
        volumes:
          - ./qdrant_data:/qdrant/storage

      postgres:
        image: postgres:16
        container_name: procurement-postgres
        restart: unless-stopped
        environment:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: agent_sessions
        ports:
          - "5432:5432"
        volumes:
          - ./pg_data:/var/lib/postgresql/data
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U postgres -d agent_sessions"]
          interval: 5s
          timeout: 3s
          retries: 5
    ```
    - `qdrant_data/` і `pg_data/` уже додані в `.gitignore`.
    - Postgres-credentials умисно дефолтні (`postgres/postgres`) — це local dev only; production credentials живуть у `.env` через `POSTGRES_URL`.
  - Status:
  - Comments:

- [ ] **Створити `scripts/setup_postgres_checkpointer.py`** —
    ```python
    """One-shot setup: створення схеми LangGraph checkpointer у Postgres.

    Запуск: python scripts/setup_postgres_checkpointer.py
    Передумова: docker compose up -d (Postgres має бути доступний).
    """
    from langgraph.checkpoint.postgres import PostgresSaver
    from config import settings


    def main() -> None:
        with PostgresSaver.from_conn_string(settings.postgres_url) as checkpointer:
            checkpointer.setup()
        print(f"Checkpointer schema initialized at {settings.postgres_url}")


    if __name__ == "__main__":
        main()
    ```
    - Запуск після `docker compose up -d`. Idempotent — `setup()` безпечно викликати багато разів.
  - Status:
  - Comments:

- [ ] **Перевірити запуск інфраструктури** — `docker compose up -d` піднімає обидва сервіси; `curl -f http://localhost:6333/healthz` повертає `200`; `docker compose exec postgres pg_isready -U postgres -d agent_sessions` повертає `accepting connections`.
  - Status:
  - Comments:

- [ ] **Виконати Postgres setup** — `python scripts/setup_postgres_checkpointer.py` має пройти без помилки і надрукувати `Checkpointer schema initialized ...`. (Це один раз; пізніше можна перевіряти через `psql -h localhost -U postgres -d agent_sessions -c '\dt'` що зʼявились таблиці `checkpoints`, `checkpoint_writes` тощо.)
  - Status:
  - Comments:

- [ ] **Очистити після перевірки** — `docker compose down` (volumes лишаються; це expected).
  - Status:
  - Comments:

### 5. Stub main.py (Checklist 0.4)

- [ ] **Переписати `main.py` як Phase-0 заглушку** —
    ```python
    """Phase-0 entry point: load settings, print Hello, run echo REPL.

    Real LangGraph wiring lands in Phase 1.7 (Lawyer single-topic) and
    Phase 2.6 (full Planner-driven graph). Until then this REPL just
    confirms config + interactive shell work.
    """
    from config import settings


    def main() -> None:
        print("Hello")
        print(f"LLM provider: {settings.llm_provider} / model: {settings.llm_model}")
        print("Echo REPL — type 'exit' to quit.")
        print("-" * 40)
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            print(f"Echo: {user_input}")


    if __name__ == "__main__":
        main()
    ```
    - **Не імпортувати** `agent` або щось з `agents/` — їх ще не існує. Імпорт лише `config`. Це гарантує що `python main.py` працює навіть з порожнім `.env`.
  - Status:
  - Comments:

- [ ] **Перевірка**: `echo "test123" | python main.py` має надрукувати `Hello`, `Echo: test123`, потім `Goodbye!` (через EOF).
  - Status:
  - Comments:

### 6. Validation & cleanup

- [ ] **Прогнати всі validation commands з нижнього розділу** — кожна має пройти зеленою. Якщо щось падає — fix + повторно. Не проходити далі.
  - Status:
  - Comments:

- [ ] **Оновити `CLAUDE.md`** — два місця: (а) "Common commands" — оновити докер-командси (`docker compose up -d` тепер для Qdrant + Postgres, MariaDB-compose тепер `docker compose -f docker-compose.ingest.yml up -d`); (б) "Project status" — root-стаби (`agent.py` etc.) видалені, layout тепер канонічний; CLAUDE.md описує не-існуючі файли.
  - Status:
  - Comments:

- [ ] **Поставити `[x]` біля Phase-0 пунктів у `docs/DELIVERY_CHECKLIST.md`** — після прогона валідації, перед commit-ом.
  - Status:
  - Comments:

- [ ] **Final smoke-тест end-to-end** — у свіжому терміналі: (1) `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`; (2) `cp .env.example .env`; (3) `docker compose up -d`; (4) `python scripts/setup_postgres_checkpointer.py`; (5) `python -c "from config import settings; print(settings.llm_model)"` → `gpt-4o`; (6) `echo 'test' | python main.py` → містить `Hello` і `Echo: test`. Усі шість кроків мають працювати у свіжому склонованому репо.
  - Status:
  - Comments:

- [ ] **Commit з префіксом `[0.x]`** — окремі коміти за фазами 0.1–0.4 (per `DELIVERY_CHECKLIST` § "Як працювати з цим документом у Claude Code"), або один консолідований `[Phase 0] Foundation scaffolding` якщо коміт chunk-ується атомарно.
  - Status:
  - Comments:

## Testing Strategy

Phase 0 — це чистий scaffold; **немає бізнес-логіки → немає unit-тестів** (це нормально, перші тести зʼявляться у Phase 1.1 для `schemas.py`). Натомість Phase 0 валідується через **smoke-тести інфраструктури**:

1. **Установка пакетів** — `pip install -r requirements.txt` у чистому venv проходить без помилок.
2. **Імпорт settings** — `python -c "from config import settings"` не падає з missing-required.
3. **Парсинг `.env`** — у CI-варіанті майбутньо: `cp .env.example .env && python -c "from config import settings; assert settings.llm_model"` має проходити з default-значеннями.
4. **CSV-валідатор** — `TECH_SUPPORT_ALLOWED_DOMAINS=a.ua,b.ua python -c "from config import settings; assert settings.tech_support_allowed_domains == ['a.ua', 'b.ua']"`. Це single-shot перевірка з командного рядка.
5. **Інфраструктура** — `docker compose up -d`, `curl -f localhost:6333/healthz`, `pg_isready` всі повертають OK.
6. **REPL** — `echo "test" | python main.py` друкує `Hello` і `Echo: test`.

DeepEval / pytest тести **не запускаються** у Phase 0 — папка `tests/` створена як placeholder, але порожня (тільки `__init__.py`).

## Acceptance Criteria

Phase 0 вважається завершеною коли:

1. ✅ Всі чек-бокси `0.1`–`0.4` у `docs/DELIVERY_CHECKLIST.md` стоять як `[x]`.
2. ✅ `find . -maxdepth 2 -type d -name "agents" -o -name "tools" -o -name "retrieval" -o -name "ingest" -o -name "observability" -o -name "prompts" -o -name "tests" -o -name "output" -o -name "docs"` повертає всі 9 директорій.
3. ✅ `find . -maxdepth 1 -name "agent.py" -o -name "ingest.py" -o -name "retriever.py" -o -name "tools.py"` повертає **пусто** (root-стаби видалені).
4. ✅ `pip install -r requirements.txt` у свіжому venv завершується без помилок.
5. ✅ `python -c "from config import settings; print(settings.llm_model)"` друкує `gpt-4o`.
6. ✅ `python -c "from config import Settings; s = Settings(tech_support_allowed_domains='a.ua,b.ua'); assert s.tech_support_allowed_domains == ['a.ua', 'b.ua']"` проходить.
7. ✅ `.env.example` містить всі поля з `Settings` (перевірка: `python -c "from config import Settings; expected = set(Settings.model_fields.keys()); print(expected)"` ↔ vs grep по `.env.example`).
8. ✅ `docker compose up -d` піднімає `qdrant` і `postgres`; `curl -f http://localhost:6333/healthz` повертає 200; `docker compose exec postgres pg_isready -U postgres -d agent_sessions` повертає `accepting connections`.
9. ✅ `python scripts/setup_postgres_checkpointer.py` друкує `Checkpointer schema initialized ...` без винятків.
10. ✅ `echo "ping" | python main.py` друкує рядки `Hello`, `Echo: ping`, `Goodbye!`.
11. ✅ `git ls-files --error-unmatch .env` падає (тобто `.env` НЕ в git); `git ls-files --error-unmatch .env.example` проходить (`.env.example` в git).
12. ✅ `README.md` ≤ 100 рядків і містить лінки на `docs/ARCHITECTURE.md` та `docs/DELIVERY_CHECKLIST.md`.
13. ✅ `CLAUDE.md` оновлено (Common commands references new docker-compose layout; root-stub disclaimer removed).

## Validation Commands

Виконуються у такому порядку. Кожна — окрема команда, копіюй у термінал.

```bash
# 1. Layout: канонічні директорії існують
ls -d agents tools retrieval ingest observability prompts tests output docs

# 2. Layout: root-стаби видалені
! ls agent.py ingest.py retriever.py tools.py 2>/dev/null

# 3. Залежності встановлюються чисто
python -m venv /tmp/phase0-venv && source /tmp/phase0-venv/bin/activate \
  && pip install -r requirements.txt && deactivate && rm -rf /tmp/phase0-venv

# 4. Settings імпортується з default-значень
python -c "from config import settings; print(settings.llm_model)"   # → gpt-4o

# 5. CSV-валідатор працює
TECH_SUPPORT_ALLOWED_DOMAINS=a.ua,b.ua \
  python -c "from config import Settings; s = Settings(); assert s.tech_support_allowed_domains == ['a.ua', 'b.ua'], s.tech_support_allowed_domains; print('OK')"

# 6. .env.example синхронізований з Settings
python -c "
from config import Settings
fields = set(Settings.model_fields.keys())
with open('.env.example') as f:
    env_keys = {line.split('=', 1)[0].strip().lower() for line in f if line.strip() and not line.startswith('#') and '=' in line}
missing = {f for f in fields if f not in env_keys}
assert not missing, f'Missing in .env.example: {missing}'
print('OK')
"

# 7. Інфраструктура піднімається
docker compose up -d
sleep 5
curl -fsS http://localhost:6333/healthz | head -1
docker compose exec -T postgres pg_isready -U postgres -d agent_sessions

# 8. LangGraph checkpointer schema створюється
python scripts/setup_postgres_checkpointer.py

# 9. main.py працює, друкує Hello, echo-loop
echo "ping" | python main.py | grep -E "(Hello|Echo: ping|Goodbye)"

# 10. Cleanup
docker compose down

# 11. .gitignore правильно ховає секрети
git check-ignore .env || echo "WARN: .env not ignored"
! git check-ignore .env.example   # .env.example має бути закомічений

# 12. CLAUDE.md і README.md оновлені
grep -F "docs/ARCHITECTURE.md" README.md
grep -F "docker-compose.ingest.yml" CLAUDE.md
```

Якщо команда #6 не працює (бо `.env.example` має не uppercase ключі або CSV-формат) — нормалізувати `.env.example` так, щоб порівняння у lowercase сходилось.

## Notes

### Залежності між пунктами

- 0.1 → 0.2: піддиректорії потрібні до `requirements.txt`-перепису, бо `tests/` зʼявляється як target для pytest, але `Settings` не залежить від layout.
- 0.2 → 0.3: `Settings` має існувати до того, як `setup_postgres_checkpointer.py` зможе імпортувати `settings.postgres_url`.
- 0.3 → 0.4: `main.py` імпортує `Settings`, який має валідуватись без помилки → той самий ланцюжок що в 0.2.
- Інфраструктура (Qdrant + Postgres) **не блокує** `main.py` Phase-0 — `main.py` не звертається ані до Qdrant, ані до Postgres. Інфра — для пропускання валідаційних smoke-тестів і готовність до Phase 1.

### Ризики і їх мітигація

- **Ризик: `pip install -r requirements.txt` фейлить через resolver-конфлікт langchain ↔ langchain-classic.** Мітигація: якщо це трапляється у валідації #3 — пінити точно `langchain==1.2.x` і `langchain-classic==1.0.x` (вибрати останні compatible). Альтернативно — прибрати `langchain-classic` якщо немає прямих імпортів (наразі немає).
- **Ризик: `langgraph-checkpoint-postgres` потребує не-default psycopg setup.** Мітигація: pinned `psycopg[binary]>=3.2` додано в requirements; якщо `setup()` падає на `connection failed` — перевірити що Postgres дійсно слухає на `localhost:5432` (з compose) і `POSTGRES_URL` у `.env` точно відповідає (за замовчуванням default-значення в `Settings` працює без `.env`).
- **Ризик: видалення root-стабів зламає десь не очікувано (наприклад в `.idea/` configs або в неочевидному імпорті).** Мітигація: перед видаленням — `grep -rE "from (agent|ingest|retriever|tools)( |$|import)" --include="*.py" .` і переконатись що нікого з них не імпортує жоден інший .py-файл (поточний `main.py` імпортує `agent` — переписуємо `main.py` ДО видалення `agent.py`).
- **Ризик: користувач очікує що PR / Phase 0 збереже існуючий README як backup.** Мітигація: контент уже у `docs/ARCHITECTURE.md` — формальної втрати немає, але якщо потрібен явний backup — файл `docs/README_legacy.md` можна додати окремим коміитом до compress-коміту README. Не передбачено в плані; додати якщо користувач попросить.

### Що НЕ робиться у Phase 0 (для уникнення scope creep)

- Жодних агентів, жодного графа, жодних промптів — це Phase 1+.
- `schemas.py` — створюється у Phase 1.1.
- Ingestion pipeline — Phase 1.3 (`ingest/run_ingest.py`).
- Retriever (semantic-only) — Phase 1.4.
- Slack Bolt setup — Phase 5.3.
- Langfuse інтеграція — Phase 7.
- Tests — Phase 1.1+ (структура `tests/` створена тут, але порожня).

### Пакети — чому ці пінги

| Пакет | Версія | Чому |
|---|---|---|
| `langchain>=1.2.0`, `langchain-core>=1.2.0` | per `CLAUDE.md` | Існуючий проєктний пін |
| `langgraph>=0.6` | latest stable | Stable API для `Send`, `PostgresSaver` |
| `langgraph-checkpoint-postgres>=2.0` | latest stable | Provides `PostgresSaver.from_conn_string` |
| `pydantic>=2.12.0`, `pydantic-settings>=2.12.0` | per `CLAUDE.md` | Існуючий проєктний пін |
| `qdrant-client>=1.13` | latest stable | Native sparse vectors (опційно для Phase 4) |
| `tavily-python>=0.5` | latest stable | Web search SDK |
| `slack-sdk>=3.30`, `slack-bolt>=1.20` | latest stable | Slack Web API + Events handler |
| `langfuse>=2.50` | latest stable | Prompt Mgmt + tracing + LLM-as-a-Judge |
| `tenacity>=9.0` | latest stable | Retry decorators (per `ARCHITECTURE § 12.1`) |
| `psycopg[binary]>=3.2` | latest stable | Required by `langgraph-checkpoint-postgres` |
| `deepeval>=2.0` | latest stable | Component / e2e LLM evals |

Якщо потрібно встановити інші — додати з пінами і обґрунтувати в commit message.
