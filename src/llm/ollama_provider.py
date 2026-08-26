"""Ollama structured-output provider implemented with langchain-ollama."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel

from src.config import AppConfig, ConfigurationError
from src.llm.base import (
    LLMConfigurationError,
    LLMInferenceError,
    LLMModelUnavailableError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMUnavailableError,
    StructuredModelT,
)


class OllamaProvider:
    """Provider adapter; it contains no insurance or routing logic."""

    def __init__(
        self,
        config: AppConfig,
        *,
        chat_model_factory: Callable[..., Any] = ChatOllama,
    ) -> None:
        if config.llm_provider != "ollama":
            raise LLMConfigurationError(
                f"Unsupported LLM_PROVIDER for OllamaProvider: {config.llm_provider}"
            )
        try:
            model = config.require_ollama_model()
        except ConfigurationError as exc:
            raise LLMConfigurationError(str(exc)) from exc

        self._model_name = model
        self._chat_model = chat_model_factory(
            model=model,
            base_url=config.ollama_base_url,
            temperature=0,
            validate_model_on_init=False,
            client_kwargs={"timeout": config.ollama_timeout_seconds},
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    def invoke_structured(
        self,
        prompt: str,
        schema: type[StructuredModelT],
    ) -> BaseModel:
        try:
            runnable = self._chat_model.with_structured_output(
                schema,
                method="json_schema",
                include_raw=True,
            )
            response = runnable.invoke(prompt)
        except Exception as exc:  # provider boundary converts vendor errors
            raise self._classify_error(exc) from exc

        if not isinstance(response, dict):
            raise LLMStructuredOutputError("Ollama returned an unexpected response envelope")
        parsing_error = response.get("parsing_error")
        if parsing_error is not None:
            raise LLMStructuredOutputError(
                f"Ollama structured output could not be parsed: {parsing_error}"
            )
        parsed = response.get("parsed")
        if parsed is None:
            raise LLMStructuredOutputError("Ollama returned no validated structured output")
        try:
            return schema.model_validate(parsed)
        except Exception as exc:
            raise LLMStructuredOutputError(
                "Ollama output failed Pydantic validation"
            ) from exc

    @staticmethod
    def _classify_error(exc: Exception) -> Exception:
        text = str(exc).casefold()
        name = type(exc).__name__.casefold()
        if isinstance(exc, TimeoutError) or "timeout" in name or "timed out" in text:
            return LLMTimeoutError("Ollama inference timed out")
        if "model" in text and ("not found" in text or "missing" in text):
            return LLMModelUnavailableError("The configured Ollama model is unavailable")
        if any(token in name for token in ("connect", "connection")) or any(
            token in text for token in ("connection refused", "failed to connect")
        ):
            return LLMUnavailableError("The Ollama service is unavailable")
        return LLMInferenceError(f"Ollama inference failed: {type(exc).__name__}")
