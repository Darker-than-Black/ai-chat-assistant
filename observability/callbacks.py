"""Langfuse CallbackHandler factory for LangGraph / LangChain."""

from __future__ import annotations

import logging
import os

from langfuse.langchain import CallbackHandler

from config import settings

logger = logging.getLogger(__name__)


def get_langfuse_handler() -> CallbackHandler | None:
    """Initialize and return the Langfuse CallbackHandler if configured.

    The new Langfuse SDK reads credentials exclusively from env vars via get_client().
    Pydantic Settings loads .env into the Settings object but not into os.environ,
    so we bridge them here before constructing the handler.
    """
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key.get_secret_value()
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key.get_secret_value()
        os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url
        return CallbackHandler()
    except Exception as e:
        logger.warning("Failed to initialize Langfuse CallbackHandler: %s", e)
        return None
