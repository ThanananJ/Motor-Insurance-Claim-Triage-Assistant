import pytest

from src.rules.risk_rules import RISK_FLAG_WORDING, evaluate_risk
from src.schemas import FactStatus


@pytest.mark.parametrize(
    ("field", "flag"),
    [
        ("suspicious_pattern", RISK_FLAG_WORDING["suspicious_pattern"]),
        ("inconsistent_story", RISK_FLAG_WORDING["inconsistent_story"]),
        ("repeated_claims", RISK_FLAG_WORDING["repeated_claims"]),
    ],
)
def test_validated_single_risk_signals(field, flag, facts_factory):
    result = evaluate_risk(facts_factory(**{field: FactStatus.TRUE}))
    assert flag in result.risk_flags


def test_severe_damage_requires_weak_evidence_for_combined_signal(facts_factory):
    severe_only = evaluate_risk(facts_factory(severe_damage=FactStatus.TRUE))
    combined = evaluate_risk(
        facts_factory(severe_damage=FactStatus.TRUE, weak_evidence=FactStatus.TRUE)
    )
    assert RISK_FLAG_WORDING["severe_damage_with_weak_evidence"] not in severe_only.risk_flags
    assert RISK_FLAG_WORDING["severe_damage_with_weak_evidence"] in combined.risk_flags


def test_risk_flag_is_not_a_fraud_conclusion(facts_factory):
    result = evaluate_risk(facts_factory(repeated_claims=FactStatus.TRUE))
    assert result.risk_flags
    assert result.fraud_conclusion is False


def test_claim_history_text_does_not_define_numeric_threshold(claim_factory, facts_factory):
    claim = claim_factory(customer_claim_history="4 claims in past 12 months")
    result = evaluate_risk(facts_factory(repeated_claims=FactStatus.UNKNOWN))
    assert claim.customer_claim_history == "4 claims in past 12 months"
    assert result.risk_flags == []
