"""Deterministic covered-event, exclusion, and date evaluation."""

from __future__ import annotations

from src.schemas import (
    ClaimFacts,
    ClaimInput,
    CoverageAssessment,
    CoverageEvaluation,
    EventType,
    FactStatus,
)


COVERED_EVENTS = {
    EventType.ACCIDENTAL_COLLISION,
    EventType.THEFT,
    EventType.FIRE,
    EventType.FLOOD,
    EventType.THIRD_PARTY_PROPERTY_DAMAGE,
}

EXCLUSION_WORDING = {
    "alcohol_or_drug_involvement": "Damage caused while driving under the influence of alcohol or drugs",
    "illegal_racing": "Damage from illegal racing",
    "intentional_damage": "Intentional damage",
    "outside_permitted_geographic_coverage": "Use of vehicle outside permitted geographic coverage",
    "late_submission": "Claim filed more than 30 days after the incident without valid reason",
}


def _submission_delay_days(claim: ClaimInput) -> int | None:
    if claim.incident_date is None or claim.claim_submitted_date is None:
        return None
    return (claim.claim_submitted_date - claim.incident_date).days


def evaluate_coverage(claim: ClaimInput, facts: ClaimFacts) -> CoverageEvaluation:
    """Evaluate only structured facts; claim_description is never interpreted."""

    if facts.event_type in COVERED_EVENTS:
        covered_status = FactStatus.TRUE
    elif facts.event_type is EventType.UNKNOWN:
        covered_status = FactStatus.UNKNOWN
    else:
        covered_status = FactStatus.FALSE

    triggered: list[str] = []
    unresolved: list[str] = []

    explicit_facts = {
        "alcohol_or_drug_involvement": facts.alcohol_or_drug_involvement,
        "illegal_racing": facts.illegal_racing,
        "intentional_damage": facts.intentional_damage,
        "outside_permitted_geographic_coverage": facts.outside_permitted_geographic_coverage,
    }
    for name, status in explicit_facts.items():
        if status is FactStatus.TRUE:
            triggered.append(EXCLUSION_WORDING[name])
        elif status is FactStatus.UNKNOWN:
            unresolved.append(f"Confirmation required: {EXCLUSION_WORDING[name]}")

    delay_days = _submission_delay_days(claim)
    if delay_days is None:
        unresolved.append("Incident Date and Claim Submitted Date are required to assess late submission")
    elif delay_days < 0:
        unresolved.append("Incident Date is after Claim Submitted Date; confirm the dates")
    elif delay_days > 30:
        if facts.late_submission_valid_reason is FactStatus.FALSE:
            triggered.append(EXCLUSION_WORDING["late_submission"])
        elif facts.late_submission_valid_reason is FactStatus.UNKNOWN:
            unresolved.append(
                f"Claim was submitted {delay_days} days after the incident "
                f"({claim.incident_date.isoformat()} to {claim.claim_submitted_date.isoformat()}), "
                "exceeding the more-than-30-day Policy condition. No valid reason for late "
                f"submission has been confirmed. Policy condition: {EXCLUSION_WORDING['late_submission']}. "
                "Late-submission exclusion may apply; route to Manual review for human confirmation."
            )

    if triggered:
        assessment = CoverageAssessment.NOT_COVERED
    elif covered_status is FactStatus.TRUE and not unresolved:
        assessment = CoverageAssessment.LIKELY_COVERED
    elif covered_status is FactStatus.TRUE:
        assessment = CoverageAssessment.POSSIBLY_COVERED
    else:
        assessment = CoverageAssessment.CANNOT_DETERMINE

    return CoverageEvaluation(
        assessment=assessment,
        is_covered_event=covered_status,
        submission_delay_days=delay_days,
        triggered_exclusions=triggered,
        unresolved_information=unresolved,
    )
