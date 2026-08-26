"""Provider-independent structured LLM contract."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class LLMProviderError(RuntimeError):
    code = "provider_error"


class LLMConfigurationError(LLMProviderError):
    code = "configuration_error"


class LLMUnavailableError(LLMProviderError):
    code = "provider_unavailable"


class LLMModelUnavailableError(LLMProviderError):
    code = "model_unavailable"


class LLMTimeoutError(LLMProviderError):
    code = "provider_timeout"


class LLMInferenceError(LLMProviderError):
    code = "inference_error"


class LLMStructuredOutputError(LLMProviderError):
    code = "structured_output_error"


@runtime_checkable
class LLMProvider(Protocol):
    """Application-facing interface; services never depend on ChatOllama."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str | None: ...

    def invoke_structured(
        self,
        prompt: str,
        schema: type[StructuredModelT],
    ) -> Any: ...
