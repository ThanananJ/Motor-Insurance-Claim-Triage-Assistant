"""Deterministic required-document comparison grounded in Policy section 3."""

from __future__ import annotations

import re

from src.schemas import ClaimInput, DocumentCheckResult, DocumentRequirement, EventType


BASE_REQUIREMENTS = (
    DocumentRequirement(identifier="claim_form", policy_wording="Claim form"),
    DocumentRequirement(
        identifier="copy_of_driving_license",
        policy_wording="Copy of driving license",
    ),
    DocumentRequirement(
        identifier="vehicle_registration",
        policy_wording="Vehicle registration",
    ),
    DocumentRequirement(identifier="photos_of_damage", policy_wording="Photos of damage"),
    DocumentRequirement(identifier="incident_report", policy_wording="Incident report"),
)

THEFT_REQUIREMENTS = (
    DocumentRequirement(
        identifier="police_report",
        policy_wording="Police report is required",
    ),
)

THIRD_PARTY_REQUIREMENTS = (
    DocumentRequirement(
        identifier="third_party_contact_information",
        policy_wording="Third-party contact information and evidence are required",
    ),
    DocumentRequirement(
        identifier="third_party_evidence",
        policy_wording="Third-party contact information and evidence are required",
    ),
)


def _normalization_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


_DOCUMENT_ALIASES = {
    "claim form": "claim_form",
    "copy of driving license": "copy_of_driving_license",
    "driving license": "copy_of_driving_license",
    "drivers license": "copy_of_driving_license",
    "driver license": "copy_of_driving_license",
    "vehicle registration": "vehicle_registration",
    "photos of damage": "photos_of_damage",
    "photo of damage": "photos_of_damage",
    "damage photos": "photos_of_damage",
    "damage photo": "photos_of_damage",
    "incident report": "incident_report",
    "police report": "police_report",
    "third party contact information": "third_party_contact_information",
    "third party contact info": "third_party_contact_information",
    "third party evidence": "third_party_evidence",
}


def normalize_document_name(document_name: str) -> str:
    """Normalize known document labels without interpreting claim narrative."""

    key = _normalization_key(document_name)
    return _DOCUMENT_ALIASES.get(key, key.replace(" ", "_"))


def required_documents(event_type: EventType) -> list[DocumentRequirement]:
    requirements: list[DocumentRequirement] = []
    if event_type is EventType.THEFT:
        requirements.extend(THEFT_REQUIREMENTS)
    elif event_type is EventType.THIRD_PARTY_PROPERTY_DAMAGE:
        requirements.extend(THIRD_PARTY_REQUIREMENTS)
    requirements.extend(BASE_REQUIREMENTS)
    return requirements


def evaluate_documents(claim: ClaimInput, event_type: EventType) -> DocumentCheckResult:
    requirements = required_documents(event_type)
    submitted = {normalize_document_name(name) for name in claim.documents_submitted}
    missing = [item for item in requirements if item.identifier not in submitted]

    missing_information: list[str] = []
    for item in missing:
        if item.policy_wording not in missing_information:
            missing_information.append(item.policy_wording)

    return DocumentCheckResult(
        required_documents=requirements,
        submitted_document_ids=sorted(submitted),
        missing_document_ids=[item.identifier for item in missing],
        missing_information=missing_information,
    )
