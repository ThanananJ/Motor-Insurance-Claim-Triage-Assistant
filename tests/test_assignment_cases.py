"""Deterministic representations of assignment fixtures; no semantic extraction."""

import json
from datetime import date
from pathlib import Path

import pytest

from src.orchestrator import analyze_claim
from src.schemas import EventType, FactStatus, Routing


FIXTURE_PATH = Path(__file__).parents[1] / "data" / "test_cases.json"


@pytest.fixture(scope="module")
def assignment_cases():
    return {item["case_id"]: item for item in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def test_case_1_missing_third_party_information_routes_manual(
    assignment_cases, claim_factory, facts_factory
):
    fixture = assignment_cases[1]
    result = analyze_claim(
        claim_factory(documents_submitted=fixture["documents_submitted"]),
        facts_factory(event_type=EventType.THIRD_PARTY_PROPERTY_DAMAGE),
    )
    assert result.recommended_routing.value in fixture["expected_routing"]
    assert "third_party_contact_information" in result.document_check.missing_document_ids
    assert result.missing_information[0] == "Third-party contact information and evidence are required"


def test_case_2_validated_illegal_racing_routes_rejection(
    assignment_cases, claim_factory, facts_factory
):
    fixture = assignment_cases[2]
    result = analyze_claim(
        claim_factory(documents_submitted=fixture["documents_submitted"]),
        facts_factory(illegal_racing=FactStatus.TRUE),
    )
    assert result.recommended_routing.value in fixture["expected_routing"]


def test_case_3_theft_without_police_report_routes_manual(
    assignment_cases, claim_factory, facts_factory
):
    fixture = assignment_cases[3]
    result = analyze_claim(
        claim_factory(documents_submitted=fixture["documents_submitted"]),
        facts_factory(event_type=EventType.THEFT),
    )
    assert result.recommended_routing.value in fixture["expected_routing"]
    assert "police_report" in result.document_check.missing_document_ids
    assert result.missing_information[0] == "Police report is required"


def test_case_4_validated_policy_risk_signals_route_fraud_review(
    assignment_cases, claim_factory, facts_factory
):
    fixture = assignment_cases[4]
    result = analyze_claim(
        claim_factory(
            documents_submitted=fixture["documents_submitted"],
            customer_claim_history=fixture["claim_history"],
        ),
        facts_factory(
            repeated_claims=FactStatus.TRUE,
            severe_damage=FactStatus.TRUE,
            weak_evidence=FactStatus.TRUE,
        ),
    )
    assert result.recommended_routing.value in fixture["expected_routing"]
    assert result.recommended_routing is Routing.FRAUD_REVIEW
    assert "Repeated claims" in result.risk.risk_flags
    assert "Severe damage with weak evidence" in result.risk.risk_flags


def test_case_5_unknown_valid_reason_routes_manual_not_forced_rejection(
    assignment_cases, claim_factory, facts_factory
):
    fixture = assignment_cases[5]
    result = analyze_claim(
        claim_factory(
            incident_date=date(2026, 1, 1),
            claim_submitted_date=date(2026, 2, 15),
            documents_submitted=fixture["documents_submitted"],
        ),
        facts_factory(
            event_type=EventType.FLOOD,
            late_submission_valid_reason=FactStatus.UNKNOWN,
        ),
    )
    assert result.recommended_routing.value in fixture["expected_routing"]
    assert result.recommended_routing is Routing.MANUAL_REVIEW
    assert result.coverage.triggered_exclusions == []
    assert result.coverage.submission_delay_days == 45
    late_reason = " ".join(result.coverage.unresolved_information)
    assert "45 days" in late_reason
    assert "more-than-30-day Policy condition" in late_reason
    assert "No valid reason for late submission has been confirmed" in late_reason
    assert "human confirmation" in late_reason
