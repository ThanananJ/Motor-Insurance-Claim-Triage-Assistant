"""Focused semantic extraction composed into one canonical ClaimFacts object."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.llm.base import LLMProvider, LLMProviderError, LLMStructuredOutputError
from src.policy.retriever import PolicyRetriever
from src.schemas import (
    ClaimFacts,
    ClaimInput,
    EventExclusionExtraction,
    EventType,
    FactStatus,
    FocusedGroupResult,
    FocusedSemanticExtractionResult,
    HistoryRiskExtraction,
    LateReasonExtraction,
)


ROOT = Path(__file__).parents[2]
EVENT_PROMPT = ROOT / "prompts" / "focused-event-exclusion-prompt.md"
RISK_PROMPT = ROOT / "prompts" / "focused-history-risk-prompt.md"
LATE_PROMPT = ROOT / "prompts" / "focused-late-reason-prompt.md"
PayloadT = TypeVar("PayloadT", bound=BaseModel)


def build_focused_prompt(
    *,
    prompt_path: Path,
    policy_context: str,
    claim_context: dict[str, Any],
    schema: type[BaseModel],
) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    replacements = {
        "{{POLICY_CONTEXT}}": policy_context,
        "{{CLAIM_CONTEXT}}": json.dumps(claim_context, ensure_ascii=False, indent=2),
        "{{OUTPUT_SCHEMA}}": json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2),
    }
    for marker, value in replacements.items():
        if marker not in template:
            raise ValueError(f"Focused prompt is missing marker: {marker}")
        template = template.replace(marker, value)
    return template


class FocusedClaimExtractor:
    """Run three bounded semantic tasks and compose their disjoint validated fields."""

    def __init__(self, provider: LLMProvider, policy_retriever: PolicyRetriever) -> None:
        self._provider = provider
        self._policy_retriever = policy_retriever

    def extract(self, claim: ClaimInput) -> FocusedSemanticExtractionResult:
        provider_name = getattr(self._provider, "provider_name", None)
        model_name = getattr(self._provider, "model_name", None)
        try:
            policy = self._policy_retriever.retrieve(claim)
            specs = [
                (
                    "event_exclusion",
                    EVENT_PROMPT,
                    {"claim_description": claim.claim_description},
                    EventExclusionExtraction,
                    self._unknown_event_exclusion(),
                ),
                (
                    "history_risk",
                    RISK_PROMPT,
                    {
                        "claim_description": claim.claim_description,
                        "customer_claim_history": claim.customer_claim_history,
                        "evidence_metadata": {"documents_submitted": claim.documents_submitted},
                    },
                    HistoryRiskExtraction,
                    self._unknown_history_risk(),
                ),
                (
                    "late_reason",
                    LATE_PROMPT,
                    {"claim_description": claim.claim_description},
                    LateReasonExtraction,
                    self._unknown_late_reason(),
                ),
            ]
        except Exception as exc:
            groups = [
                FocusedGroupResult(
                    group=name,
                    success=False,
                    latency_seconds=0,
                    error=f"Focused extraction setup failed: {type(exc).__name__}",
                    error_code="extraction_unavailable",
                )
                for name in ("event_exclusion", "history_risk", "late_reason")
            ]
            return FocusedSemanticExtractionResult(
                success=False,
                facts=ClaimFacts(),
                groups=groups,
                failed_groups=[item.group for item in groups],
                provider=provider_name,
                model=model_name,
            )

        outputs: list[BaseModel] = []
        group_results: list[FocusedGroupResult] = []
        failed_groups: list[str] = []
        for name, prompt_path, context, schema, fallback in specs:
            prompt = build_focused_prompt(
                prompt_path=prompt_path,
                policy_context=policy,
                claim_context=context,
                schema=schema,
            )
            payload, result = self._run_group(name, prompt, schema, fallback)
            outputs.append(payload)
            group_results.append(result)
            if not result.success:
                failed_groups.append(name)

        composed: dict[str, Any] = {}
        for output in outputs:
            composed.update(output.model_dump())
        facts = ClaimFacts.model_validate(composed)
        return FocusedSemanticExtractionResult(
            success=not failed_groups,
            facts=facts,
            groups=group_results,
            failed_groups=failed_groups,
            provider=provider_name,
            model=model_name,
        )

    def _run_group(
        self,
        name: str,
        prompt: str,
        schema: type[PayloadT],
        fallback: PayloadT,
    ) -> tuple[PayloadT, FocusedGroupResult]:
        started = time.perf_counter()
        retry_count = 0
        while True:
            try:
                candidate = self._provider.invoke_structured(prompt, schema)
                payload = schema.model_validate(candidate)
                return payload, FocusedGroupResult(
                    group=name,
                    success=True,
                    retry_count=retry_count,
                    latency_seconds=time.perf_counter() - started,
                )
            except LLMStructuredOutputError as exc:
                if retry_count == 0:
                    retry_count = 1
                    prompt = self._retry_prompt(prompt)
                    continue
                error, code = str(exc), exc.code
            except LLMProviderError as exc:
                error, code = str(exc), exc.code
            except (ValidationError, ValueError, TypeError):
                if retry_count == 0:
                    retry_count = 1
                    prompt = self._retry_prompt(prompt)
                    continue
                error, code = "Focused output failed Pydantic validation", "validation_error"
            except Exception as exc:
                error, code = (
                    f"Focused extraction is unavailable: {type(exc).__name__}",
                    "extraction_unavailable",
                )
            return fallback, FocusedGroupResult(
                group=name,
                success=False,
                retry_count=retry_count,
                latency_seconds=time.perf_counter() - started,
                error=error,
                error_code=code,
            )

    @staticmethod
    def _retry_prompt(prompt: str) -> str:
        return (
            prompt
            + "\n\n<schema_correction>Your previous output was structurally invalid. "
            + "Return every required field once using only allowed enum values, with no "
            + "prose or extra fields.</schema_correction>"
        )

    @staticmethod
    def _unknown_event_exclusion() -> EventExclusionExtraction:
        return EventExclusionExtraction(
            event_type=EventType.UNKNOWN,
            alcohol_or_drug_involvement=FactStatus.UNKNOWN,
            illegal_racing=FactStatus.UNKNOWN,
            intentional_damage=FactStatus.UNKNOWN,
            outside_permitted_geographic_coverage=FactStatus.UNKNOWN,
        )

    @staticmethod
    def _unknown_history_risk() -> HistoryRiskExtraction:
        return HistoryRiskExtraction(
            suspicious_pattern=FactStatus.UNKNOWN,
            inconsistent_story=FactStatus.UNKNOWN,
            repeated_claims=FactStatus.UNKNOWN,
            severe_damage=FactStatus.UNKNOWN,
            weak_evidence=FactStatus.UNKNOWN,
        )

    @staticmethod
    def _unknown_late_reason() -> LateReasonExtraction:
        return LateReasonExtraction(late_submission_valid_reason=FactStatus.UNKNOWN)
