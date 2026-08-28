from types import SimpleNamespace

import pytest

from app import FACT_FIELDS, build_claim_input, confirm_with_service, load_demo_case, prepare_with_service
from src.schemas import ClaimFacts
from src.services.triage_service import TriageService


class StubExtractor:
    def __init__(self, facts=None, *, fail=False):
        self.facts = ClaimFacts.model_validate(facts or {})
        self.fail = fail
        self.calls = 0

    def extract(self, claim):
        self.calls += 1
        if self.fail:
            raise RuntimeError("ollama unavailable")
        return SimpleNamespace(success=True, facts=self.facts, provider="fake", model="fake", failed_groups=[])


class GuardService:
    def __init__(self):
        self.calls = 0

    def confirm_and_analyze(self, review, confirmation):
        self.calls += 1
        raise AssertionError("must not be called without confirmation")


def values(**overrides):
    return tuple(ClaimFacts.model_validate(overrides).model_dump(mode="json")[field] for field in FACT_FIELDS)


def claim_values(case_id):
    loaded = load_demo_case(f"Assignment Case {case_id}")
    return loaded, build_claim_input(*loaded)


def test_claim_input_is_built_from_ui_values():
    claim = build_claim_input("UI-1", "Customer", "Vehicle", "Flood damage", "No prior claims", "2026-01-01", "2026-02-15", ["Claim form"])
    assert claim.claim_id == "UI-1"
    assert (claim.claim_submitted_date - claim.incident_date).days == 45
    assert claim.documents_submitted == ["Claim form"]


def test_prepare_uses_service_and_populates_editable_fact_values():
    extractor = StubExtractor({"event_type": "theft", "repeated_claims": "true"})
    result = prepare_with_service(TriageService(extractor), "UI-2", "", "", "Stolen", "", "", "", [])
    assert extractor.calls == 1
    assert result[2] == "theft"
    assert result[2 + FACT_FIELDS.index("repeated_claims")] == "true"
    assert result[-1] is False


def test_confirmation_false_cannot_call_final_analysis():
    guard = GuardService()
    output = confirm_with_service(guard, object(), False, *values())
    assert guard.calls == 0
    assert "confirm" in output[-1].casefold()


def test_confirmation_true_creates_confirmed_facts_and_corrected_values_reach_p2():
    loaded, claim = claim_values(1)
    service = TriageService(StubExtractor({"repeated_claims": "true"}))
    review = service.prepare_claim(claim)
    output = confirm_with_service(service, review, True, *values(event_type="third_party_property_damage", repeated_claims="false"))
    assert output[3] == "Manual review"
    assert output[4] in {"High", "Medium", "Low"}
    assert "Third-party contact information and evidence are required" in output[1]
    assert "Pending Human Claim Officer Review" in output[-1]


def test_assignment_history_phrase_is_suggested_for_human_confirmation():
    loaded, _ = claim_values(4)
    prepared = prepare_with_service(TriageService(StubExtractor()), *loaded)
    assert prepared[2 + FACT_FIELDS.index("repeated_claims")] == "true"
    assert prepared[-1] is False


@pytest.mark.parametrize(
    ("case_id", "proposal", "corrected", "expected"),
    [
        (1, {"repeated_claims": "true"}, {"event_type": "third_party_property_damage", "repeated_claims": "false"}, "Manual review"),
        (4, {}, {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"}, "Fraud review"),
        (5, {"outside_permitted_geographic_coverage": "true"}, {"event_type": "flood", "outside_permitted_geographic_coverage": "unknown", "late_submission_valid_reason": "unknown"}, "Manual review"),
    ],
)
def test_critical_assignment_demo_corrections(case_id, proposal, corrected, expected):
    loaded, claim = claim_values(case_id)
    service = TriageService(StubExtractor(proposal))
    review = service.prepare_claim(claim)
    output = confirm_with_service(service, review, True, *values(**corrected))
    assert output[3] == expected


def test_extraction_failure_still_allows_manual_confirmation_and_p0():
    loaded, claim = claim_values(4)
    service = TriageService(StubExtractor(fail=True))
    prepared = prepare_with_service(service, *loaded)
    review = prepared[0]
    assert review.proposal.source == "safe_fallback"
    assert "unavailable" in prepared[1].casefold()
    output = confirm_with_service(service, review, True, *values(repeated_claims="true", severe_damage="true", weak_evidence="true"))
    assert output[3] == "Fraud review"
