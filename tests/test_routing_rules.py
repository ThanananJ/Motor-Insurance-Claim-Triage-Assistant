from src.orchestrator import analyze_claim
from src.schemas import EventType, FactStatus, Routing


def test_complete_clear_covered_claim_routes_standard(claim_factory, facts_factory):
    result = analyze_claim(claim_factory(), facts_factory())
    assert result.recommended_routing is Routing.STANDARD_PROCESSING


def test_incomplete_documents_route_manual(claim_factory, facts_factory):
    result = analyze_claim(
        claim_factory(documents_submitted=["Claim form"]),
        facts_factory(),
    )
    assert result.recommended_routing is Routing.MANUAL_REVIEW


def test_unknown_required_information_routes_manual(claim_factory, facts_factory):
    result = analyze_claim(
        claim_factory(incident_date=None),
        facts_factory(),
    )
    assert result.recommended_routing is Routing.MANUAL_REVIEW


def test_explicit_exclusion_has_rejection_precedence(claim_factory, facts_factory):
    result = analyze_claim(
        claim_factory(documents_submitted=[]),
        facts_factory(illegal_racing=FactStatus.TRUE, repeated_claims=FactStatus.TRUE),
    )
    assert result.recommended_routing is Routing.REJECTION_REVIEW


def test_validated_risk_has_fraud_precedence_over_missing_documents(claim_factory, facts_factory):
    result = analyze_claim(
        claim_factory(documents_submitted=[]),
        facts_factory(repeated_claims=FactStatus.TRUE),
    )
    assert result.recommended_routing is Routing.FRAUD_REVIEW


def test_unknown_event_routes_manual(claim_factory, facts_factory):
    result = analyze_claim(
        claim_factory(),
        facts_factory(event_type=EventType.UNKNOWN),
    )
    assert result.recommended_routing is Routing.MANUAL_REVIEW
