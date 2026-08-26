from typing import Any

import pytest

from src.config import AppConfig
from src.llm.base import (
    LLMConfigurationError,
    LLMInferenceError,
    LLMModelUnavailableError,
    LLMProvider,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from src.llm.ollama_provider import OllamaProvider
from src.schemas import SemanticExtractionPayload
from tests.p1_fakes import extraction_payload


class FakeRunnable:
    def __init__(self, response: Any = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def invoke(self, prompt: str):
        assert prompt
        if self.error:
            raise self.error
        return self.response


class FakeChatModel:
    def __init__(self, response: Any = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.structured_args = None

    def with_structured_output(self, schema, **kwargs):
        self.structured_args = (schema, kwargs)
        return FakeRunnable(self.response, self.error)


def provider_with_chat(chat: FakeChatModel) -> OllamaProvider:
    def factory(**kwargs):
        assert kwargs["model"] == "configured-model"
        assert kwargs["temperature"] == 0
        return chat

    return OllamaProvider(
        AppConfig(ollama_model="configured-model"),
        chat_model_factory=factory,
    )


def test_provider_contract_and_successful_structured_response():
    chat = FakeChatModel(
        {"raw": object(), "parsed": extraction_payload(event_type="theft"), "parsing_error": None}
    )
    provider = provider_with_chat(chat)
    result = provider.invoke_structured("prompt", SemanticExtractionPayload)
    assert isinstance(provider, LLMProvider)
    assert result.facts.event_type.value == "theft"
    assert chat.structured_args[1] == {"method": "json_schema", "include_raw": True}


def test_provider_requires_explicit_model_configuration():
    with pytest.raises(LLMConfigurationError, match="OLLAMA_MODEL"):
        OllamaProvider(AppConfig(ollama_model=None))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("timed out"), LLMTimeoutError),
        (ConnectionError("connection refused"), LLMUnavailableError),
        (RuntimeError("model configured-model not found"), LLMModelUnavailableError),
        (RuntimeError("unexpected provider failure"), LLMInferenceError),
    ],
)
def test_provider_classifies_inference_failures(error, expected):
    provider = provider_with_chat(FakeChatModel(error=error))
    with pytest.raises(expected):
        provider.invoke_structured("prompt", SemanticExtractionPayload)


@pytest.mark.parametrize(
    "response",
    [
        "unrestricted prose",
        {"raw": object(), "parsed": None, "parsing_error": None},
        {"raw": object(), "parsed": None, "parsing_error": ValueError("bad JSON")},
    ],
)
def test_provider_rejects_malformed_structured_responses(response):
    provider = provider_with_chat(FakeChatModel(response))
    with pytest.raises(LLMStructuredOutputError):
        provider.invoke_structured("prompt", SemanticExtractionPayload)
