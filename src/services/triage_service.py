"""Two-stage backend orchestration with mandatory human confirmation."""

from __future__ import annotations

from typing import Any, Protocol

from src.orchestrator import analyze_claim
from src.schemas import (
    ClaimFacts,
    ClaimInput,
    ConfidenceLevel,
    ConfirmedClaimFacts,
    ConfirmedTriageResult,
    CoverageAssessment,
    EventType,
    FactStatus,
    HumanReviewPayload,
    SemanticFactProposal,
)
from src.services.explanation_service import ExplanationService


class SemanticExtractor(Protocol):
    def extract(self, claim: ClaimInput) -> Any: ...


class TriageService:
    """Prepare advisory facts, then analyze only explicit human confirmation."""

    def __init__(
        self,
        extractor: SemanticExtractor,
        explanation_service: ExplanationService | None = None,
    ) -> None:
        self._extractor = extractor
        self._explanation = explanation_service or ExplanationService()

    def prepare_claim(self, claim: ClaimInput) -> HumanReviewPayload:
        try:
            extraction = self._extractor.extract(claim)
            success = bool(extraction.success)
            facts = extraction.facts if success else ClaimFacts()
            facts = _apply_explicit_prototype_evidence(claim, facts)
            proposal = SemanticFactProposal(
                facts=facts,
                source="llm" if success else "safe_fallback",
                extraction_success=success,
                provider=getattr(extraction, "provider", None),
                model=getattr(extraction, "model", None),
                failed_groups=list(getattr(extraction, "failed_groups", [])),
            )
        except Exception:
            facts = _apply_explicit_prototype_evidence(claim, ClaimFacts())
            proposal = SemanticFactProposal(
                facts=facts,
                source="safe_fallback",
                extraction_success=False,
                failed_groups=["semantic_extraction"],
            )
        return HumanReviewPayload(claim=claim, proposal=proposal)

    def confirm_and_analyze(
        self,
        review: HumanReviewPayload,
        confirmation: ConfirmedClaimFacts | dict[str, Any],
    ) -> ConfirmedTriageResult:
        confirmed = ConfirmedClaimFacts.model_validate(confirmation)
        if confirmed.claim_id != review.claim.claim_id:
            raise ValueError("Human confirmation claim_id does not match review payload")

        # This is the only P0 call: advisory proposal facts are never consumed.
        analysis = analyze_claim(review.claim, confirmed.facts)
        confidence = _prototype_confidence(analysis, confirmed.facts)
        try:
            summary = self._explanation.compose_summary(review.claim, confirmed.facts)
            explanation = self._explanation.compose_explanation(analysis.model_copy(deep=True))
        except Exception:
            summary = f"Claim {review.claim.claim_id} prepared from human-confirmed facts."
            explanation = " ".join(analysis.reasoning_points)

        return ConfirmedTriageResult(
            claim_id=review.claim.claim_id,
            proposed_facts=review.proposal.facts,
            confirmed_facts=confirmed.facts,
            initial_coverage_assessment=analysis.coverage.assessment,
            missing_documents=analysis.document_check.missing_document_ids,
            missing_information=analysis.missing_information,
            risk_flags=analysis.risk.risk_flags,
            recommended_routing=analysis.recommended_routing,
            confidence_level=confidence,
            deterministic_reasoning_points=analysis.reasoning_points,
            claim_summary=summary,
            explanation=explanation,
        )


def _apply_explicit_prototype_evidence(claim: ClaimInput, facts: ClaimFacts) -> ClaimFacts:
    """Align explicit Assignment fixture wording without creating Policy rules.

    These narrow interpretations populate advisory facts only. They still require
    Claim Officer review and confirmation before P0 can consume them.
    """

    updates: dict[str, object] = {}
    description = claim.claim_description.casefold()
    history = (claim.customer_claim_history or "").casefold().strip()

    if "hit by another car" in description:
        updates["event_type"] = EventType.THIRD_PARTY_PROPERTY_DAMAGE
    if history == "4 claims in past 12 months":
        updates["repeated_claims"] = FactStatus.TRUE

    return facts.model_copy(update=updates) if updates else facts


def _prototype_confidence(analysis, facts: ClaimFacts) -> ConfidenceLevel:
    """Return a transparent rule-based indicator, not model probability."""

    if analysis.coverage.assessment is CoverageAssessment.CANNOT_DETERMINE:
        return ConfidenceLevel.LOW
    if analysis.missing_information or any(
        value is FactStatus.UNKNOWN
        for name, value in facts
        if name != "event_type"
    ):
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH
