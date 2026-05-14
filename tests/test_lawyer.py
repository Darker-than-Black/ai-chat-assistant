from __future__ import annotations

from pydantic import SecretStr

from agents.lawyer import OpenAIFunctionCallingChat, get_llm


def test_openai_structured_output_defaults_to_function_calling(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_with_structured_output(self, schema=None, **kwargs):
        captured["schema"] = schema
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(
        "langchain_openai.chat_models.base.BaseChatOpenAI.with_structured_output",
        fake_with_structured_output,
    )

    llm = OpenAIFunctionCallingChat(model="gpt-4.1-mini", api_key="test-key")
    sentinel = object()

    llm.with_structured_output(sentinel)

    assert captured["schema"] is sentinel
    assert captured["kwargs"]["method"] == "function_calling"


def test_openai_structured_output_preserves_explicit_method(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_with_structured_output(self, schema=None, **kwargs):
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(
        "langchain_openai.chat_models.base.BaseChatOpenAI.with_structured_output",
        fake_with_structured_output,
    )

    llm = OpenAIFunctionCallingChat(model="gpt-4.1-mini", api_key="test-key")
    llm.with_structured_output(object(), method="json_schema")

    assert captured["kwargs"]["method"] == "json_schema"


def test_get_llm_returns_openai_wrapper(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_model", "gpt-4.1-mini")
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-key"))

    llm = get_llm()

    assert isinstance(llm, OpenAIFunctionCallingChat)
