from src.rules.document_rules import evaluate_documents, normalize_document_name
from src.schemas import EventType


def test_base_required_documents_are_complete(claim_factory):
    result = evaluate_documents(claim_factory(), EventType.ACCIDENTAL_COLLISION)
    assert result.missing_document_ids == []
    assert len(result.required_documents) == 5


def test_missing_base_document_is_reported_with_policy_wording(claim_factory):
    claim = claim_factory(documents_submitted=["Claim form"])
    result = evaluate_documents(claim, EventType.ACCIDENTAL_COLLISION)
    assert "copy_of_driving_license" in result.missing_document_ids
    assert "Copy of driving license" in result.missing_information


def test_theft_requires_police_report(claim_factory):
    result = evaluate_documents(claim_factory(), EventType.THEFT)
    assert "police_report" in result.missing_document_ids
    assert "Police report is required" in result.missing_information


def test_third_party_damage_requires_contact_and_evidence(claim_factory):
    result = evaluate_documents(claim_factory(), EventType.THIRD_PARTY_PROPERTY_DAMAGE)
    assert "third_party_contact_information" in result.missing_document_ids
    assert "third_party_evidence" in result.missing_document_ids
    assert result.missing_information.count(
        "Third-party contact information and evidence are required"
    ) == 1


def test_document_normalization_accepts_known_label_variants(claim_factory):
    claim = claim_factory(
        documents_submitted=[
            " CLAIM-FORM ",
            "Driving License",
            "vehicle_registration",
            "Damage Photos",
            "incident-report",
        ]
    )
    result = evaluate_documents(claim, EventType.ACCIDENTAL_COLLISION)
    assert result.missing_document_ids == []
    assert normalize_document_name("Third Party Contact Info") == "third_party_contact_information"
