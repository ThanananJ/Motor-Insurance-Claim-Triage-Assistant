from types import SimpleNamespace

import pytest

from app import (
    FACT_FIELDS,
    clear_result_ui,
    confirm_with_service,
    load_demo_case,
    prepare_with_service,
    reset_review_ui,
)
from src.schemas import ClaimFacts
from src.services.triage_service import TriageService


class StubExtractor:
    def __init__(self, facts=None):
        self.facts = ClaimFacts.model_validate(facts or {})

    def extract(self, claim):
        return SimpleNamespace(
            success=True,
            facts=self.facts,
            provider="fake",
            model="advisory",
            failed_groups=[],
        )


def fact_values(**overrides):
    facts = ClaimFacts.model_validate(overrides).model_dump(mode="json")
    return tuple(facts[field] for field in FACT_FIELDS)


def test_claim_change_invalidates_review_confirmation_and_result_state():
    reset = reset_review_ui()
    assert reset[0] is None
    assert "Analyze this claim" in reset[1]
    assert reset[2 : 2 + len(FACT_FIELDS)] == fact_values()
    assert reset[2 + len(FACT_FIELDS)] is False
    assert reset[3 + len(FACT_FIELDS)] == ""
    assert "Pending Human Claim Officer Review" in reset[-1]


def test_new_analysis_clears_previous_result_panel():
    cleared = clear_result_ui()
    assert cleared[:8] == (
        "", "No result yet.", "No result yet.", "", "No result yet.",
        "No result yet.", "", "",
    )
    assert "Pending Human Claim Officer Review" in cleared[-1]


@pytest.mark.parametrize(
    ("case_id", "proposal", "confirmed", "expected"),
    [
        (1, {"repeated_claims": "true"}, {"event_type": "third_party_property_damage", "repeated_claims": "false"}, "Manual review"),
        (2, {}, {"event_type": "accidental_collision", "illegal_racing": "true"}, "Rejection review"),
        (3, {}, {"event_type": "theft"}, "Manual review"),
        (4, {}, {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"}, "Fraud review"),
        (5, {"outside_permitted_geographic_coverage": "true"}, {"event_type": "flood", "outside_permitted_geographic_coverage": "unknown", "late_submission_valid_reason": "unknown"}, "Manual review"),
    ],
)
def test_all_assignment_cases_complete_ui_service_workflow(case_id, proposal, confirmed, expected):
    values = load_demo_case(f"Assignment Case {case_id}")
    service = TriageService(StubExtractor(proposal))
    review = prepare_with_service(service, *values)[0]

    result = confirm_with_service(service, review, True, *fact_values(**confirmed))

    assert result[3] == expected
    assert "Pending Human Claim Officer Review" in result[-1]


def test_repeated_prepare_and_confirm_actions_remain_safe():
    values = load_demo_case("Assignment Case 4")
    service = TriageService(StubExtractor())
    first_review = prepare_with_service(service, *values)[0]
    second_review = prepare_with_service(service, *values)[0]
    confirmed = fact_values(repeated_claims="true", severe_damage="true", weak_evidence="true")

    first_result = confirm_with_service(service, first_review, True, *confirmed)
    second_result = confirm_with_service(service, second_review, True, *confirmed)

    assert first_result[3] == second_result[3] == "Fraud review"
    assert "Repeated claims" in first_result[2]
    assert "Severe damage with weak evidence" in first_result[2]
