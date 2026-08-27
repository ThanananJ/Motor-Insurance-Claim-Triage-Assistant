"""Minimum, non-authoritative composition around immutable P0 results."""

from src.schemas import ClaimFacts, ClaimInput, DeterministicAnalysisResult


class ExplanationService:
    """Compose deterministic fallback text without changing analysis fields."""

    def compose_summary(self, claim: ClaimInput, facts: ClaimFacts) -> str:
        event = facts.event_type.value.replace("_", " ")
        return f"Claim {claim.claim_id}: {event} event reported. {claim.claim_description}"

    def compose_explanation(self, analysis: DeterministicAnalysisResult) -> str:
        return " ".join(analysis.reasoning_points)
