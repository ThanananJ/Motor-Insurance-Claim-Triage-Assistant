import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.schemas import ClaimFacts, ConfidenceLevel, ConfirmedClaimFacts, Routing
from src.services.triage_service import TriageService


CASES = {
    item["case_id"]: item
    for item in json.loads((Path(__file__).parents[1] / "data" / "test_cases.json").read_text(encoding="utf-8"))
}


class StubExtractor:
    def __init__(self, facts=None, *, error=None):
        self.facts = ClaimFacts.model_validate(facts or {})
        self.error = error

    def extract(self, claim):
        if self.error:
            raise self.error
        return SimpleNamespace(
            success=True, facts=self.facts, provider="fake", model="advisory",
            failed_groups=[],
        )


class MutatingExplanation:
    def compose_summary(self, claim, facts):
        return "Optional summary"

    def compose_explanation(self, analysis):
        analysis.recommended_routing = Routing.STANDARD_PROCESSING
        return "Optional explanation cannot alter the deterministic result"


class FailingExplanation:
    def compose_summary(self, claim, facts):
        raise RuntimeError("unavailable")


def confirmed(claim_id, **facts):
    return ConfirmedClaimFacts(
        claim_id=claim_id,
        facts=ClaimFacts.model_validate(facts),
        confirmed_by_human=True,
    )


def test_prepare_returns_unconfirmed_advisory_proposal(claim_factory):
    service = TriageService(StubExtractor({"repeated_claims": "true"}))
    review = service.prepare_claim(claim_factory(claim_id="P2-PREPARE"))
    assert review.confirmation_required is True
    assert review.proposal.confirmed is False
    assert review.proposal.source == "llm"
    assert review.proposal.facts.repeated_claims.value == "true"


def test_explicit_assignment_context_aligns_advisory_facts_but_still_requires_confirmation(claim_factory):
    service = TriageService(StubExtractor())
    third_party = service.prepare_claim(
        claim_factory(claim_description="Parked vehicle was hit by another car at a shopping mall")
    )
    repeated = service.prepare_claim(
        claim_factory(customer_claim_history="4 claims in past 12 months")
    )
    assert third_party.proposal.facts.event_type.value == "third_party_property_damage"
    assert repeated.proposal.facts.repeated_claims.value == "true"
    assert third_party.proposal.confirmed is False
    assert repeated.confirmation_required is True


def test_unconfirmed_facts_are_rejected_before_p0(claim_factory):
    review = TriageService(StubExtractor()).prepare_claim(claim_factory(claim_id="P2-NO"))
    with pytest.raises(ValidationError):
        TriageService(StubExtractor()).confirm_and_analyze(
            review,
            {"claim_id": "P2-NO", "facts": {}, "confirmed_by_human": False},
        )


def test_officer_correction_prevents_false_positive_fraud(claim_factory):
    claim = claim_factory(claim_id="P2-CORRECT", documents_submitted=[])
    service = TriageService(StubExtractor({"repeated_claims": "true"}))
    review = service.prepare_claim(claim)
    result = service.confirm_and_analyze(review, confirmed(claim.claim_id, repeated_claims="false"))
    assert result.proposed_facts.repeated_claims.value == "true"
    assert result.confirmed_facts.repeated_claims.value == "false"
    assert result.recommended_routing is Routing.MANUAL_REVIEW
    assert result.human_confirmation_status == "confirmed"


def test_llm_failure_returns_unknown_proposal_and_workflow_continues(claim_factory):
    claim = claim_factory(claim_id="P2-FALLBACK")
    service = TriageService(StubExtractor(error=RuntimeError("ollama unavailable")))
    review = service.prepare_claim(claim)
    assert review.proposal.source == "safe_fallback"
    assert review.proposal.facts == ClaimFacts()
    result = service.confirm_and_analyze(review, confirmed(claim.claim_id, event_type="theft"))
    assert result.recommended_routing is Routing.MANUAL_REVIEW


def test_explanation_failure_falls_back_without_blocking(claim_factory):
    claim = claim_factory(claim_id="P2-EXPLAIN")
    service = TriageService(StubExtractor(), FailingExplanation())
    result = service.confirm_and_analyze(service.prepare_claim(claim), confirmed(claim.claim_id))
    assert result.explanation == " ".join(result.deterministic_reasoning_points)


def test_explanation_cannot_mutate_deterministic_routing(claim_factory):
    claim = claim_factory(claim_id="P2-IMMUTABLE")
    service = TriageService(StubExtractor(), MutatingExplanation())
    result = service.confirm_and_analyze(service.prepare_claim(claim), confirmed(claim.claim_id))
    assert result.recommended_routing is Routing.MANUAL_REVIEW


def test_confidence_is_rule_based_enum_not_percentage(claim_factory):
    claim = claim_factory(claim_id="P2-CONFIDENCE")
    service = TriageService(StubExtractor())
    result = service.confirm_and_analyze(
        service.prepare_claim(claim),
        confirmed(claim.claim_id),
    )
    assert result.confidence_level in set(ConfidenceLevel)
    assert result.confidence_level.value in {"High", "Medium", "Low"}
    assert "%" not in result.confidence_level.value


@pytest.mark.parametrize(
    ("case_id", "proposed", "human_facts", "expected"),
    [
        (1, {"event_type": "accidental_collision", "repeated_claims": "true"}, {"event_type": "third_party_property_damage", "repeated_claims": "false"}, Routing.MANUAL_REVIEW),
        (2, {"event_type": "accidental_collision", "illegal_racing": "true"}, {"event_type": "accidental_collision", "illegal_racing": "true", "repeated_claims": "false"}, Routing.REJECTION_REVIEW),
        (3, {"event_type": "theft"}, {"event_type": "theft", "repeated_claims": "false"}, Routing.MANUAL_REVIEW),
        (4, {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"}, {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"}, Routing.FRAUD_REVIEW),
        (5, {"event_type": "flood", "outside_permitted_geographic_coverage": "true", "late_submission_valid_reason": "false"}, {"event_type": "flood", "outside_permitted_geographic_coverage": "unknown", "late_submission_valid_reason": "unknown"}, Routing.MANUAL_REVIEW),
    ],
)
def test_assignment_cases_through_human_confirmation(case_id, proposed, human_facts, expected, claim_factory):
    fixture = CASES[case_id]
    overrides = {
        "claim_id": f"P2-CASE-{case_id}",
        "claim_description": fixture["scenario"],
        "documents_submitted": fixture["documents_submitted"],
        "customer_claim_history": fixture["claim_history"],
    }
    if case_id == 5:
        overrides.update(incident_date=date(2026, 1, 1), claim_submitted_date=date(2026, 2, 15))
    claim = claim_factory(**overrides)
    service = TriageService(StubExtractor(proposed))
    review = service.prepare_claim(claim)
    result = service.confirm_and_analyze(review, confirmed(claim.claim_id, **human_facts))
    assert result.recommended_routing is expected
    assert result.recommendation_disclaimer.endswith("final decision maker.")
    if case_id == 4:
        assert "Severe damage with weak evidence" in result.risk_flags
    if case_id == 5:
        assert result.initial_coverage_assessment.value != "Not covered"
