"""Pydantic Settings — single source of truth for runtime configuration.

All environment variables are loaded here. No other module should call
os.environ directly; import `settings` instead.

Phase-0 invariant: every secret is Optional[SecretStr] with default None,
so `Settings()` validates with an empty .env. Components that need a
specific key (LLM, Tavily, Slack, Langfuse) will assert it themselves
when first used in Phase 1+.
"""
from __future__ import annotations
from typing import Annotated, Literal
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM ───────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"

    # ── GitHub search ─────────────────────────────────────────────────
    github_api_token: SecretStr | None = None
    # owner/repo strings; full GitHub URLs are normalized by _normalize_github_repos
    tech_support_github_repos: Annotated[list[str], NoDecode] = Field(
        default_factory=list
    )

    # ── Web search (Tavily) ───────────────────────────────────────────
    tavily_api_key: SecretStr | None = None
    # NoDecode disables pydantic-settings' JSON-decode of list-typed env
    # values, so the CSV validator below receives the raw string.
    # Host-only values are canonical (e.g. "docs.prozorro.org"); full URLs
    # are normalized to bare hosts by _normalize_allowed_domains.
    tech_support_allowed_domains: Annotated[list[str], NoDecode] = Field(
        default_factory=list
    )
    tech_support_tag_whitelist: Annotated[list[str], NoDecode] = Field(
        default_factory=list
    )

    # ── Vector DB (Qdrant) ────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_laws_collection: str = "laws"
    qdrant_articles_collection: str = "articles"
    laws_freshness_threshold_days: int = 180
    articles_freshness_threshold_days: int = 365

    # ── Hybrid retrieval ──────────────────────────────────────────────
    retrieval_top_k: int = 20
    hybrid_semantic_weight: float = 0.6
    hybrid_bm25_weight: float = 0.4

    # ── Reranking ─────────────────────────────────────────────────────
    enable_reranker: bool = True
    reranker_model: str = "BAAI/bge-reranker-base"
    rerank_top_k: int = 5
    rerank_score_threshold: float = 0.3

    # ── Postgres (LangGraph checkpointer) ─────────────────────────────
    postgres_url: str = (
        "postgresql://postgres:postgres@localhost:5432/agent_sessions"
    )
    session_ttl_hours: int = 24

    # ── Runtime ───────────────────────────────────────────────────────
    port: int = 3000

    # ── Slack ─────────────────────────────────────────────────────────
    slack_app_token: SecretStr | None = None       # xapp-... required for Socket Mode
    slack_bot_token: SecretStr | None = None
    slack_signing_secret: SecretStr | None = None  # required only for HTTP mode
    slack_user_channel_id: str | None = None
    slack_expert_channel_id: str | None = None

    # ── Confluence ────────────────────────────────────────────────────
    confluence_url: str | None = None
    confluence_username: str | None = None
    confluence_api_token: SecretStr | None = None
    confluence_space_keys: Annotated[list[str], NoDecode] = Field(
        default_factory=list
    )

    # ── Agent behavior ────────────────────────────────────────────────
    critic_max_retries: int = 3
    # After the first revision cycle, approve if avg of three Critic scores >= this.
    # Guards against a Critic that demands perfect citations RAG can't always provide.
    critic_min_approve_score: float = 0.5
    worker_timeout_seconds: int = 60
    planner_max_subtasks: int = 3

    # ── Observability (Langfuse) ──────────────────────────────────────
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    @field_validator(
        "tech_support_allowed_domains",
        "tech_support_tag_whitelist",
        "confluence_space_keys",
        "tech_support_github_repos",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("tech_support_allowed_domains", mode="after")
    @classmethod
    def _normalize_allowed_domains(cls, v: list[str]) -> list[str]:
        result = []
        for domain in v:
            if "://" in domain:
                domain = domain.split("://", 1)[1]
            domain = domain.split("/")[0].strip()
            if domain:
                result.append(domain)
        return result

    @field_validator("tech_support_github_repos", mode="after")
    @classmethod
    def _normalize_github_repos(cls, v: list[str]) -> list[str]:
        result = []
        for repo in v:
            if "github.com/" in repo:
                repo = repo.split("github.com/", 1)[1].rstrip("/")
            repo = repo.strip()
            if repo:
                result.append(repo)
        return result


settings = Settings()
