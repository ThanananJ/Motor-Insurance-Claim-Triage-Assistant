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

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AppConfig":
        values = os.environ if environ is None else environ
        provider = values.get("LLM_PROVIDER", "ollama").strip().casefold()
        base_url = values.get("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        model = values.get("OLLAMA_MODEL", "").strip() or None
        timeout_text = values.get("OLLAMA_TIMEOUT_SECONDS", "60").strip()
        try:
            timeout = float(timeout_text)
        except ValueError as exc:
            raise ConfigurationError("OLLAMA_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0:
            raise ConfigurationError("OLLAMA_TIMEOUT_SECONDS must be greater than zero")
        return cls(
            llm_provider=provider,
            ollama_base_url=base_url,
            ollama_model=model,
            ollama_timeout_seconds=timeout,
        )

    def require_ollama_model(self) -> str:
        if not self.ollama_model:
            raise ConfigurationError(
                "OLLAMA_MODEL is not configured; select a model for the target hardware"
            )
        return self.ollama_model
