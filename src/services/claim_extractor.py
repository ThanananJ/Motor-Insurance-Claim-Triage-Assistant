"""Application boundary for safe semantic ClaimFacts extraction."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.base import LLMStructuredOutputError
from src.policy.retriever import PolicyRetriever
from src.schemas import (
    ClaimFacts,
    ClaimInput,
    LLMExtractionPayload,
    SemanticExtractionPayload,
    SemanticExtractionResult,
)


DEFAULT_EXTRACTION_PROMPT_PATH = (
    Path(__file__).parents[2] / "prompts" / "triage-system-prompt.md"
)


class PromptTemplateError(RuntimeError):
    pass


def build_extraction_prompt(
    claim: ClaimInput,
    policy_context: str,
    *,
    prompt_path: Path = DEFAULT_EXTRACTION_PROMPT_PATH,
) -> str:
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromptTemplateError(f"Unable to load extraction prompt: {prompt_path}") from exc

    replacements = {
        "{{POLICY_CONTEXT}}": policy_context,
        "{{CLAIM_CONTEXT}}": json.dumps(
            claim.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        "{{OUTPUT_SCHEMA}}": json.dumps(
            LLMExtractionPayload.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        ),
    }
    for marker, value in replacements.items():
        if marker not in template:
            raise PromptTemplateError(f"Extraction prompt is missing marker: {marker}")
        template = template.replace(marker, value)
    return template


class ClaimExtractor:
    def __init__(
        self,
        provider: LLMProvider,
        policy_retriever: PolicyRetriever,
        *,
        prompt_path: Path = DEFAULT_EXTRACTION_PROMPT_PATH,
    ) -> None:
        self._provider = provider
        self._policy_retriever = policy_retriever
        self._prompt_path = prompt_path

    def extract(self, claim: ClaimInput) -> SemanticExtractionResult:
        provider_name = getattr(self._provider, "provider_name", None)
        model_name = getattr(self._provider, "model_name", None)
        try:
            policy_context = self._policy_retriever.retrieve(claim)
            prompt = build_extraction_prompt(
                claim,
                policy_context,
                prompt_path=self._prompt_path,
            )
        except Exception as exc:
            return self._failure(
                f"Semantic extraction is unavailable: {type(exc).__name__}",
                "extraction_unavailable",
                provider_name,
                model_name,
                retry_count=0,
            )

        retry_count = 0
        while True:
            try:
                candidate = self._provider.invoke_structured(
                    prompt,
                    LLMExtractionPayload,
                )
                payload = self._to_canonical_payload(candidate)
                break
            except LLMStructuredOutputError as exc:
                if retry_count == 0:
                    retry_count = 1
                    prompt = self._retry_prompt(prompt)
                    continue
                return self._failure(
                    str(exc),
                    exc.code,
                    provider_name,
                    model_name,
                    retry_count=retry_count,
                )
            except LLMProviderError as exc:
                return self._failure(
                    str(exc),
                    exc.code,
                    provider_name,
                    model_name,
                    retry_count=retry_count,
                )
            except (ValidationError, ValueError, TypeError):
                if retry_count == 0:
                    retry_count = 1
                    prompt = self._retry_prompt(prompt)
                    continue
                return self._failure(
                    "Semantic output failed Pydantic validation",
                    "validation_error",
                    provider_name,
                    model_name,
                    retry_count=retry_count,
                )
            except Exception as exc:
                return self._failure(
                    f"Semantic extraction is unavailable: {type(exc).__name__}",
                    "extraction_unavailable",
                    provider_name,
                    model_name,
                    retry_count=retry_count,
                )

        return SemanticExtractionResult(
            success=True,
            facts=payload.facts,
            evidence=payload.evidence,
            provider=provider_name,
            model=model_name,
            retry_count=retry_count,
        )

    @staticmethod
    def _to_canonical_payload(candidate: object) -> SemanticExtractionPayload:
        """Convert the flat LLM contract while retaining legacy provider compatibility."""

        try:
            llm_payload = LLMExtractionPayload.model_validate(candidate)
        except ValidationError:
            return SemanticExtractionPayload.model_validate(candidate)
        return SemanticExtractionPayload(
            facts=ClaimFacts.model_validate(llm_payload.model_dump()),
            evidence=[],
        )

    @staticmethod
    def _retry_prompt(prompt: str) -> str:
        return (
            prompt
            + "\n\n<schema_correction>\n"
            + "Your previous output did not match the required schema. Return every "
            + "required field exactly once, using only the allowed enum values. Do not "
            + "add prose or any extra fields.\n"
            + "</schema_correction>"
        )

    @staticmethod
    def _failure(
        message: str,
        code: str,
        provider: str | None,
        model: str | None,
        *,
        retry_count: int,
    ) -> SemanticExtractionResult:
        return SemanticExtractionResult(
            success=False,
            facts=ClaimFacts(),
            evidence=[],
            error=message,
            error_code=code,
            provider=provider,
            model=model,
            retry_count=retry_count,
        )
