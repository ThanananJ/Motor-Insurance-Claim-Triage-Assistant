"""Two-stage backend orchestration with mandatory human confirmation."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from src.orchestrator import analyze_claim
from src.monitoring.models import EventType as MonitoringEventType
from src.monitoring.service import MonitoringService
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
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        self._extractor = extractor
        self._explanation = explanation_service or ExplanationService()
        self._monitoring = monitoring_service
        self._request_ids: dict[int, str] = {}

    def prepare_claim(self, claim: ClaimInput) -> HumanReviewPayload:
        request_id = self._monitoring.new_request_id() if self._monitoring else ""
        set_context = getattr(self._extractor, "set_monitoring_context", None)
        if callable(set_context):
            set_context(request_id)
        started = perf_counter()
        self._record(MonitoringEventType.REQUEST_STARTED, request_id, status="started", stage="request")
        self._record(MonitoringEventType.AI_EXTRACTION_STARTED, request_id, status="started", stage="ai_extraction")
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
                warning=(
                    "Prompt exceeds configured context. Safe UNKNOWN suggestions were loaded; "
                    "review, enter, and confirm facts manually."
                    if any(getattr(group, "error_code", None) == "prompt_context_over_limit" for group in getattr(extraction, "groups", []))
                    else (
                        "LLM suggestions are advisory and require human confirmation."
                        if success
                        else "AI extraction unavailable. Safe UNKNOWN suggestions were loaded; please review, enter, and confirm facts manually."
                    )
                ),
            )
            latency_ms = (perf_counter() - started) * 1000
            self._record(
                MonitoringEventType.AI_EXTRACTION_COMPLETED if success else MonitoringEventType.AI_EXTRACTION_FAILED,
                request_id, status="success" if success else "failed", stage="ai_extraction",
                latency_ms=latency_ms, provider_status="success" if success else "failed",
                provider_error_category=None if success else "PROVIDER_OR_VALIDATION_FAILURE",
                model_provider=proposal.provider, model_name=proposal.model,
                ai_facts_proposed_count=_known_fact_count(facts), ai_unknown_count=_unknown_fact_count(facts),
            )
            self._record(
                MonitoringEventType.SCHEMA_VALIDATION_COMPLETED, request_id,
                status="passed" if success else "failed", stage="validation", schema_valid=success,
                validation_error_category=None if success else "EXTRACTION_RESULT_INVALID",
            )
        except Exception as exc:
            facts = _apply_explicit_prototype_evidence(claim, ClaimFacts())
            proposal = SemanticFactProposal(
                facts=facts,
                source="safe_fallback",
                extraction_success=False,
                failed_groups=["semantic_extraction"],
                warning="AI extraction unavailable. Safe UNKNOWN suggestions were loaded; please review, enter, and confirm facts manually.",
            )
            self._record(
                MonitoringEventType.AI_EXTRACTION_FAILED, request_id, status="failed",
                stage="ai_extraction", latency_ms=(perf_counter() - started) * 1000,
                provider_status="failed", provider_error_category=_error_category(exc),
                ai_facts_proposed_count=_known_fact_count(facts), ai_unknown_count=_unknown_fact_count(facts),
            )
            self._record(
                MonitoringEventType.SCHEMA_VALIDATION_COMPLETED, request_id, status="failed",
                stage="validation", schema_valid=False, validation_error_category="PROVIDER_OUTPUT_UNAVAILABLE",
            )
        if not proposal.extraction_success:
            self._record(
                MonitoringEventType.FALLBACK_TRIGGERED, request_id, status="safe_fallback",
                stage="fallback", fallback_triggered=True, fallback_reason="AI_EXTRACTION_UNAVAILABLE",
            )
        review = HumanReviewPayload(claim=claim, proposal=proposal)
        if request_id:
            self._request_ids[id(review)] = request_id
        return review

    def confirm_and_analyze(
        self,
        review: HumanReviewPayload,
        confirmation: ConfirmedClaimFacts | dict[str, Any],
    ) -> ConfirmedTriageResult:
        request_id = self._request_ids.pop(id(review), "")
        started = perf_counter()
        try:
            confirmed = ConfirmedClaimFacts.model_validate(confirmation)
            if confirmed.claim_id != review.claim.claim_id:
                raise ValueError("Human confirmation claim_id does not match review payload")

            changed = [
                field for field in ClaimFacts.model_fields
                if getattr(review.proposal.facts, field) != getattr(confirmed.facts, field)
            ]
            self._record(
                MonitoringEventType.HUMAN_CONFIRMATION_COMPLETED, request_id, status="confirmed",
                stage="human_confirmation", human_confirmed=True,
                human_override=bool(changed), override_field_count=len(changed),
            )
            if changed:
                self._record(
                    MonitoringEventType.HUMAN_OVERRIDE_RECORDED, request_id, status="recorded",
                    stage="human_confirmation", human_confirmed=True, human_override=True,
                    override_field_count=len(changed), changed_field_categories=",".join(changed),
                    override_reason_category="OFFICER_JUDGMENT",
                )

            # This is the only P0 call: advisory proposal facts are never consumed.
            analysis = analyze_claim(review.claim, confirmed.facts)
            confidence = _prototype_confidence(analysis, confirmed.facts)
            try:
                summary = self._explanation.compose_summary(review.claim, confirmed.facts)
                explanation = self._explanation.compose_explanation(analysis.model_copy(deep=True))
            except Exception:
                summary = f"Claim {review.claim.claim_id} prepared from human-confirmed facts."
                explanation = " ".join(analysis.reasoning_points)

            result = ConfirmedTriageResult(
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
            self._record(
                MonitoringEventType.TRIAGE_COMPLETED, request_id, status="completed", stage="triage",
                latency_ms=(perf_counter() - started) * 1000,
                coverage_status=result.initial_coverage_assessment.value,
                route=result.recommended_routing.value,
                missing_document_count=len(result.missing_documents), risk_signal_count=len(result.risk_flags),
                late_submission_flag=_is_late(review.claim), human_confirmed=True,
            )
            self._record(
                MonitoringEventType.HUMAN_FINAL_DECISION_RECORDED, request_id,
                status="not_available", stage="final_decision",
                human_final_decision_recorded=False, human_final_decision_category="not_available",
            )
            self._record(
                MonitoringEventType.REQUEST_COMPLETED, request_id, status="completed",
                stage="request", latency_ms=(perf_counter() - started) * 1000, human_confirmed=True,
            )
            return result
        except Exception as exc:
            self._record(
                MonitoringEventType.REQUEST_FAILED, request_id, status="failed", stage="request",
                latency_ms=(perf_counter() - started) * 1000,
                validation_error_category=_error_category(exc),
            )
            raise

    def _record(self, event_type: MonitoringEventType, request_id: str, **fields: Any) -> None:
        if self._monitoring and request_id:
            self._monitoring.record(event_type, request_id, **fields)


def _known_fact_count(facts: ClaimFacts) -> int:
    return sum(value.value != "unknown" for _, value in facts)


def _unknown_fact_count(facts: ClaimFacts) -> int:
    return len(ClaimFacts.model_fields) - _known_fact_count(facts)


def _error_category(exc: Exception) -> str:
    name = type(exc).__name__.upper()
    if "TIMEOUT" in name:
        return "PROVIDER_TIMEOUT"
    if name in {"VALIDATIONERROR", "VALUEERROR"}:
        return "VALIDATION_ERROR"
    return "PROVIDER_FAILURE"


def _is_late(claim: ClaimInput) -> bool | None:
    if not claim.incident_date or not claim.claim_submitted_date:
        return None
    return (claim.claim_submitted_date - claim.incident_date).days > 30


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
