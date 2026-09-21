"""Qwen chat-template prompt token preflight with fail-open semantics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Callable

from src.config import AppConfig


TOKENIZER_NAME = "Qwen/Qwen2.5-3B-Instruct"
MODEL_CAPABILITY_CONTEXT_TOKENS = 131072


@dataclass(frozen=True)
class PromptTokenResult:
    token_count_available: bool
    tokenizer_name: str = TOKENIZER_NAME
    token_count_source: str = "qwen_chat_template"
    prompt_token_count: int | None = None
    token_count_error_category: str | None = None
    model_capability_context_tokens: int = MODEL_CAPABILITY_CONTEXT_TOKENS
    effective_context_window_tokens: int = 32768
    reserved_output_tokens: int = 256
    max_prompt_tokens: int = 32512
    remaining_prompt_capacity_tokens: int | None = None
    context_usage_percent: float | None = None
    context_status: str = "UNKNOWN"
    over_prompt_limit: bool | None = None
    context_source: str = "application_num_ctx"

    def monitoring_fields(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=1)
def _load_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(TOKENIZER_NAME)


class PromptTokenCounter:
    def __init__(
        self,
        config: AppConfig,
        *,
        tokenizer_loader: Callable[[], Any] = _load_tokenizer,
    ) -> None:
        self.config = config
        self._tokenizer_loader = tokenizer_loader

    def count(self, assembled_prompt: str) -> PromptTokenResult:
        maximum = self.config.ollama_num_ctx - self.config.reserved_output_tokens
        base = {
            "effective_context_window_tokens": self.config.ollama_num_ctx,
            "reserved_output_tokens": self.config.reserved_output_tokens,
            "max_prompt_tokens": maximum,
        }
        try:
            tokenizer = self._tokenizer_loader()
            encoded = tokenizer.apply_chat_template(
                [{"role": "user", "content": assembled_prompt}],
                tokenize=True,
                add_generation_prompt=True,
            )
            count = len(encoded)
        except Exception:
            return PromptTokenResult(
                token_count_available=False,
                token_count_error_category="TOKENIZER_UNAVAILABLE",
                **base,
            )
        usage = count / maximum * 100
        if usage > 100:
            status = "OVER_LIMIT"
        elif usage >= self.config.prompt_token_critical_percent:
            status = "CRITICAL"
        elif usage >= self.config.prompt_token_warning_percent:
            status = "WARNING"
        else:
            status = "HEALTHY"
        return PromptTokenResult(
            token_count_available=True,
            prompt_token_count=count,
            remaining_prompt_capacity_tokens=maximum - count,
            context_usage_percent=usage,
            context_status=status,
            over_prompt_limit=count > maximum,
            **base,
        )
