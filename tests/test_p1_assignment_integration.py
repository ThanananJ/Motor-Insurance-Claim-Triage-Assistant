"""P1 fake-provider integration into the unchanged P0 deterministic core."""

import json
from datetime import date
from pathlib import Path

import pytest

from src.orchestrator import analyze_claim
from src.schemas import Routing
from src.services.claim_extractor import ClaimExtractor
from tests.p1_fakes import FakeProvider, FixedPolicyRetriever, extraction_payload


CASES = {
    item["case_id"]: item
    for item in json.loads(
        (Path(__file__).parents[1] / "data" / "test_cases.json").read_text(encoding="utf-8")
    )
}


@pytest.mark.parametrize(
    ("case_id", "facts", "expected"),
    [
        (1, {"event_type": "third_party_property_damage"}, Routing.MANUAL_REVIEW),
        (2, {"event_type": "accidental_collision", "illegal_racing": "true"}, Routing.REJECTION_REVIEW),
        (3, {"event_type": "theft"}, Routing.MANUAL_REVIEW),
        (
            4,
            {
                "event_type": "accidental_collision",
                "repeated_claims": "true",
                "severe_damage": "true",
                "weak_evidence": "true",
            },
            Routing.FRAUD_REVIEW,
        ),
        (5, {"event_type": "flood", "late_submission_valid_reason": "unknown"}, Routing.MANUAL_REVIEW),
    ],
)
def test_assignment_case_through_fake_semantic_provider(
    case_id,
    facts,
    expected,
    claim_factory,
):
    fixture = CASES[case_id]
    claim_overrides = {
        "claim_id": f"CASE-{case_id}",
        "claim_description": fixture["scenario"],
        "documents_submitted": fixture["documents_submitted"],
        "customer_claim_history": fixture["claim_history"],
    }
    if case_id == 5:
        claim_overrides.update(
            incident_date=date(2026, 1, 1),
            claim_submitted_date=date(2026, 2, 15),
        )
    claim = claim_factory(**claim_overrides)
    extractor = ClaimExtractor(
        FakeProvider(extraction_payload(**facts)),
        FixedPolicyRetriever(),
    )

    extraction = extractor.extract(claim)
    assert extraction.success is True
    result = analyze_claim(claim, extraction.facts)
    assert result.recommended_routing is expected
