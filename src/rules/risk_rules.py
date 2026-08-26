"""Deterministic handling of validated Policy risk signals."""

from src.schemas import ClaimFacts, FactStatus, RiskEvaluation


RISK_FLAG_WORDING = {
    "suspicious_pattern": "Suspicious pattern",
    "inconsistent_story": "Inconsistent story",
    "repeated_claims": "Repeated claims",
    "severe_damage_with_weak_evidence": "Severe damage with weak evidence",
}


def evaluate_risk(facts: ClaimFacts) -> RiskEvaluation:
    flags: list[str] = []
    if facts.suspicious_pattern is FactStatus.TRUE:
        flags.append(RISK_FLAG_WORDING["suspicious_pattern"])
    if facts.inconsistent_story is FactStatus.TRUE:
        flags.append(RISK_FLAG_WORDING["inconsistent_story"])
    if facts.repeated_claims is FactStatus.TRUE:
        flags.append(RISK_FLAG_WORDING["repeated_claims"])
    if facts.severe_damage is FactStatus.TRUE and facts.weak_evidence is FactStatus.TRUE:
        flags.append(RISK_FLAG_WORDING["severe_damage_with_weak_evidence"])

    # A risk signal routes work for review; it is never proof or a fraud verdict.
    return RiskEvaluation(risk_flags=flags, fraud_conclusion=False)
