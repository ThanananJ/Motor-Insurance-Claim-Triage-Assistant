from __future__ import annotations

from typing import Any

from src.llm.base import LLMProviderError, LLMStructuredOutputError
from src.schemas import (
    EventExclusionExtraction,
    EventType,
    FactStatus,
    HistoryRiskExtraction,
    LateReasonExtraction,
)
from src.services.focused_claim_extractor import FocusedClaimExtractor
from tests.p1_fakes import FixedPolicyRetriever


class GroupUnavailable(LLMProviderError):
    code = "group_unavailable"


class FocusedFakeProvider:
    provider_name = "fake"
    model_name = "focused-fake"

    def __init__(self, *, fail_schema: type | None = None, malformed_once: type | None = None):
        self.fail_schema = fail_schema
        self.malformed_once = malformed_once
        self.calls: list[tuple[str, type]] = []

    def invoke_structured(self, prompt: str, schema: type) -> Any:
        self.calls.append((prompt, schema))
        if schema is self.fail_schema:
            raise GroupUnavailable("focused group unavailable")
        if schema is self.malformed_once:
            self.malformed_once = None
            raise LLMStructuredOutputError("missing required field")
        if schema is EventExclusionExtraction:
            return {
                "event_type": "theft",
                "alcohol_or_drug_involvement": "unknown",
                "illegal_racing": "unknown",
                "intentional_damage": "unknown",
                "outside_permitted_geographic_coverage": "unknown",
            }
        if schema is HistoryRiskExtraction:
            return {
                "suspicious_pattern": "unknown",
                "inconsistent_story": "unknown",
                "repeated_claims": "true",
                "severe_damage": "true",
                "weak_evidence": "true",
            }
        if schema is LateReasonExtraction:
            return {"late_submission_valid_reason": "false"}
        raise AssertionError(f"Unexpected schema: {schema}")


def test_focused_groups_compose_one_canonical_claim_facts(claim_factory):
    provider = FocusedFakeProvider()
    claim = claim_factory(
        claim_description="Vehicle stolen with severe damage and unclear evidence.",
        customer_claim_history="Several recent claims",
    )
    result = FocusedClaimExtractor(provider, FixedPolicyRetriever()).extract(claim)
    assert result.success is True
    assert result.facts.event_type is EventType.THEFT
    assert result.facts.repeated_claims is FactStatus.TRUE
    assert result.facts.severe_damage is FactStatus.TRUE
    assert result.facts.weak_evidence is FactStatus.TRUE
    assert result.facts.late_submission_valid_reason is FactStatus.FALSE
    assert [schema for _, schema in provider.calls] == [
        EventExclusionExtraction,
        HistoryRiskExtraction,
        LateReasonExtraction,
    ]


def test_input_routing_limits_each_group_context(claim_factory):
    provider = FocusedFakeProvider()
    claim = claim_factory(
        claim_description="DESCRIPTION_MARKER",
        customer_claim_history="HISTORY_MARKER",
        documents_submitted=["EVIDENCE_MARKER"],
    )
    FocusedClaimExtractor(provider, FixedPolicyRetriever()).extract(claim)
    event_prompt, risk_prompt, late_prompt = [prompt for prompt, _ in provider.calls]
    assert "DESCRIPTION_MARKER" in event_prompt
    assert "HISTORY_MARKER" not in event_prompt
    assert "EVIDENCE_MARKER" not in event_prompt
    assert "DESCRIPTION_MARKER" in risk_prompt
    assert "HISTORY_MARKER" in risk_prompt
    assert "EVIDENCE_MARKER" in risk_prompt
    assert "DESCRIPTION_MARKER" in late_prompt
    assert "HISTORY_MARKER" not in late_prompt
    assert "incident_date" not in late_prompt


def test_failed_group_falls_back_only_its_fields_to_unknown(claim_factory):
    provider = FocusedFakeProvider(fail_schema=HistoryRiskExtraction)
    result = FocusedClaimExtractor(provider, FixedPolicyRetriever()).extract(claim_factory())
    assert result.success is False
    assert result.failed_groups == ["history_risk"]
    assert result.facts.event_type is EventType.THEFT
    assert result.facts.repeated_claims is FactStatus.UNKNOWN
    assert result.facts.severe_damage is FactStatus.UNKNOWN
    assert result.facts.weak_evidence is FactStatus.UNKNOWN
    assert result.facts.late_submission_valid_reason is FactStatus.FALSE
    assert result.groups[1].retry_count == 0


def test_structural_failure_retries_only_failed_group_once(claim_factory):
    provider = FocusedFakeProvider(malformed_once=HistoryRiskExtraction)
    result = FocusedClaimExtractor(provider, FixedPolicyRetriever()).extract(claim_factory())
    assert result.success is True
    assert result.groups[1].retry_count == 1
    assert len(provider.calls) == 4
    retry_prompt = provider.calls[2][0]
    assert "<schema_correction>" in retry_prompt


def test_focused_schemas_expose_no_routing_or_decision_fields():
    text = " ".join(
        str(schema.model_json_schema()).casefold()
        for schema in (EventExclusionExtraction, HistoryRiskExtraction, LateReasonExtraction)
    )
    assert "recommended_routing" not in text
    assert "final_decision" not in text
    assert "approval" not in text
    assert "submission_delay_days" not in text
