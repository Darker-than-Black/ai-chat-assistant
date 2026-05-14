"""Langfuse client singleton and Prompt Management wrapper.

Prompts are the source of truth in Langfuse. There is no local fallback —
if Langfuse is unreachable or the prompt is missing, a RuntimeError is raised
so the failure is explicit rather than silently degraded.
"""

from __future__ import annotations

import logging

from langfuse import Langfuse

from config import settings

logger = logging.getLogger(__name__)

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse | None:
    """Return the Langfuse singleton client, or None if not configured."""
    global _langfuse
    if _langfuse is None:
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            return None
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            host=settings.langfuse_base_url,
        )
    return _langfuse


def load_prompt(name: str, label: str = "production", **kwargs) -> str:
    """Load a compiled prompt from Langfuse Prompt Management.

    Raises RuntimeError if Langfuse is not configured or the prompt cannot
    be fetched/compiled, so failures are always visible.
    """
    langfuse = get_langfuse()
    if langfuse is None:
        raise RuntimeError(
            f"Langfuse is not configured — cannot load prompt '{name}'. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env."
        )

    try:
        prompt_obj = langfuse.get_prompt(name, label=label)
        compiled = prompt_obj.compile(**kwargs)
        logger.debug("Loaded prompt '%s' from Langfuse (label=%s, %d chars)", name, label, len(compiled))
        return compiled
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load prompt '{name}' (label='{label}') from Langfuse: {exc}"
        ) from exc
