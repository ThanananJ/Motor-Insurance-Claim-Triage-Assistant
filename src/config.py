"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    ollama_timeout_seconds: float = 60.0
    ollama_num_ctx: int = 32768
    reserved_output_tokens: int = 256
    prompt_token_warning_percent: float = 70.0
    prompt_token_critical_percent: float = 85.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AppConfig":
        values = os.environ if environ is None else environ
        provider = values.get("LLM_PROVIDER", "ollama").strip().casefold()
        base_url = values.get("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        model = values.get("OLLAMA_MODEL", "").strip() or None
        timeout_text = values.get("OLLAMA_TIMEOUT_SECONDS", "60").strip()
        num_ctx_text = values.get("OLLAMA_NUM_CTX", "32768").strip()
        reserved_text = values.get("OLLAMA_RESERVED_OUTPUT_TOKENS", "256").strip()
        warning_text = values.get("PROMPT_TOKEN_WARNING_PERCENT", "70").strip()
        critical_text = values.get("PROMPT_TOKEN_CRITICAL_PERCENT", "85").strip()
        try:
            timeout = float(timeout_text)
            num_ctx = int(num_ctx_text)
            reserved = int(reserved_text)
            warning = float(warning_text)
            critical = float(critical_text)
        except ValueError as exc:
            raise ConfigurationError("Ollama context and prompt-token settings must be numeric") from exc
        if timeout <= 0:
            raise ConfigurationError("OLLAMA_TIMEOUT_SECONDS must be greater than zero")
        if num_ctx <= 0 or reserved < 0 or reserved >= num_ctx:
            raise ConfigurationError("OLLAMA_NUM_CTX must exceed OLLAMA_RESERVED_OUTPUT_TOKENS")
        if not 0 < warning < critical <= 100:
            raise ConfigurationError("Prompt-token thresholds must satisfy 0 < warning < critical <= 100")
        return cls(
            llm_provider=provider,
            ollama_base_url=base_url,
            ollama_model=model,
            ollama_timeout_seconds=timeout,
            ollama_num_ctx=num_ctx,
            reserved_output_tokens=reserved,
            prompt_token_warning_percent=warning,
            prompt_token_critical_percent=critical,
        )

    def require_ollama_model(self) -> str:
        if not self.ollama_model:
            raise ConfigurationError(
                "OLLAMA_MODEL is not configured; select a model for the target hardware"
            )
        return self.ollama_model
