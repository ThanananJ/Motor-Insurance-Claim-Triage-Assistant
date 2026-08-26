from datetime import date

import pytest

from src.schemas import ClaimFacts, ClaimInput, EventType, FactStatus


ALL_BASE_DOCUMENTS = [
    "Claim form",
    "Copy of driving license",
    "Vehicle registration",
    "Photos of damage",
    "Incident report",
]


@pytest.fixture
def claim_factory():
    def factory(**overrides) -> ClaimInput:
        values = {
            "claim_id": "TEST-001",
            "incident_date": date(2026, 1, 1),
            "claim_submitted_date": date(2026, 1, 10),
            "claim_description": "Structured facts are supplied separately.",
            "documents_submitted": list(ALL_BASE_DOCUMENTS),
        }
        values.update(overrides)
        return ClaimInput(**values)

    return factory


@pytest.fixture
def facts_factory():
    def factory(**overrides) -> ClaimFacts:
        values = {
            "event_type": EventType.ACCIDENTAL_COLLISION,
            "alcohol_or_drug_involvement": FactStatus.FALSE,
            "illegal_racing": FactStatus.FALSE,
            "intentional_damage": FactStatus.FALSE,
            "outside_permitted_geographic_coverage": FactStatus.FALSE,
            "late_submission_valid_reason": FactStatus.UNKNOWN,
            "suspicious_pattern": FactStatus.FALSE,
            "inconsistent_story": FactStatus.FALSE,
            "repeated_claims": FactStatus.FALSE,
            "severe_damage": FactStatus.FALSE,
            "weak_evidence": FactStatus.FALSE,
        }
        values.update(overrides)
        return ClaimFacts(**values)

    return factory
