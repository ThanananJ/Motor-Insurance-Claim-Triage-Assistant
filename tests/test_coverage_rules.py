from datetime import date

import pytest

from src.rules.coverage_rules import EXCLUSION_WORDING, evaluate_coverage
from src.schemas import CoverageAssessment, EventType, FactStatus


@pytest.mark.parametrize(
    "event_type",
    [
        EventType.ACCIDENTAL_COLLISION,
        EventType.THEFT,
        EventType.FIRE,
        EventType.FLOOD,
        EventType.THIRD_PARTY_PROPERTY_DAMAGE,
    ],
)
def test_policy_covered_events(event_type, claim_factory, facts_factory):
    result = evaluate_coverage(claim_factory(), facts_factory(event_type=event_type))
    assert result.assessment is CoverageAssessment.LIKELY_COVERED


@pytest.mark.parametrize(
    ("field", "policy_key"),
    [
        ("illegal_racing", "illegal_racing"),
        ("alcohol_or_drug_involvement", "alcohol_or_drug_involvement"),
        ("intentional_damage", "intentional_damage"),
        (
            "outside_permitted_geographic_coverage",
            "outside_permitted_geographic_coverage",
        ),
    ],
)
def test_explicit_exclusions(field, policy_key, claim_factory, facts_factory):
    result = evaluate_coverage(
        claim_factory(),
        facts_factory(**{field: FactStatus.TRUE}),
    )
    assert result.assessment is CoverageAssessment.NOT_COVERED
    assert EXCLUSION_WORDING[policy_key] in result.triggered_exclusions


def test_submission_at_30_days_does_not_trigger_exclusion(claim_factory, facts_factory):
    claim = claim_factory(
        incident_date=date(2026, 1, 1),
        claim_submitted_date=date(2026, 1, 31),
    )
    result = evaluate_coverage(claim, facts_factory())
    assert result.submission_delay_days == 30
    assert EXCLUSION_WORDING["late_submission"] not in result.triggered_exclusions


def test_late_submission_without_valid_reason_triggers_exclusion(claim_factory, facts_factory):
    claim = claim_factory(
        incident_date=date(2026, 1, 1),
        claim_submitted_date=date(2026, 2, 15),
    )
    result = evaluate_coverage(
        claim,
        facts_factory(late_submission_valid_reason=FactStatus.FALSE),
    )
    assert result.submission_delay_days == 45
    assert EXCLUSION_WORDING["late_submission"] in result.triggered_exclusions


def test_late_submission_with_valid_reason_does_not_trigger_exclusion(claim_factory, facts_factory):
    claim = claim_factory(
        incident_date=date(2026, 1, 1),
        claim_submitted_date=date(2026, 2, 15),
    )
    result = evaluate_coverage(
        claim,
        facts_factory(late_submission_valid_reason=FactStatus.TRUE),
    )
    assert result.assessment is CoverageAssessment.LIKELY_COVERED
    assert EXCLUSION_WORDING["late_submission"] not in result.triggered_exclusions


def test_late_submission_with_unknown_reason_preserves_uncertainty(claim_factory, facts_factory):
    claim = claim_factory(
        incident_date=date(2026, 1, 1),
        claim_submitted_date=date(2026, 2, 15),
    )
    result = evaluate_coverage(claim, facts_factory())
    assert result.assessment is CoverageAssessment.POSSIBLY_COVERED
    assert result.triggered_exclusions == []
    assert "Valid reason for submission more than 30 days after the incident" in result.unresolved_information


def test_unknown_fact_is_not_silently_false(claim_factory):
    from src.schemas import ClaimFacts

    result = evaluate_coverage(claim_factory(), ClaimFacts(event_type=EventType.ACCIDENTAL_COLLISION))
    assert result.assessment is CoverageAssessment.POSSIBLY_COVERED
    assert result.unresolved_information


def test_claim_description_keywords_do_not_create_facts(claim_factory, facts_factory):
    claim = claim_factory(claim_description="I was in an illegal race")
    result = evaluate_coverage(claim, facts_factory())
    assert result.triggered_exclusions == []
