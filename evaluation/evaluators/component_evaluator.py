"""Controlled component checks with fault attribution."""

from __future__ import annotations

import time
from types import SimpleNamespace

from pydantic import ValidationError

from evaluation import POLICY_VERSION, PROMPT_VERSION
from evaluation.metrics import ratio, summarize_results
from evaluation.schemas import CaseResult, EvaluationDataset, EvaluationReport
from src.llm.base import LLMUnavailableError
from src.orchestrator import analyze_claim
from src.policy.loader import PolicyLoader
from src.schemas import ClaimFacts, ClaimInput, ConfirmedClaimFacts, EventExclusionExtraction
from src.services.focused_claim_extractor import EVENT_PROMPT, build_focused_prompt
from src.services.triage_service import TriageService


class _Extractor:
    def __init__(self, fail: bool = False): self.fail = fail
    def extract(self, claim):
        if self.fail: raise LLMUnavailableError("synthetic unavailable")
        return SimpleNamespace(success=True, facts=ClaimFacts(), provider="fixture", model=None, failed_groups=[])


def _complete_docs() -> list[str]:
    return ["Claim form", "Copy of driving license", "Vehicle registration", "Photos of damage", "Incident report"]


def _run(component: str) -> tuple[bool, dict, str | None]:
    claim = ClaimInput(claim_id="SYN-COMP", claim_description="Synthetic collision", incident_date="2026-01-01", claim_submitted_date="2026-01-02", documents_submitted=_complete_docs())
    if component == "prompt_builder":
        prompt = build_focused_prompt(prompt_path=EVENT_PROMPT, policy_context=PolicyLoader().load_exact(), claim_context={"claim_description": "UNTRUSTED_MARKER"}, schema=EventExclusionExtraction)
        ok = all(x in prompt for x in ["UNTRUSTED_MARKER", "illegal_racing", "Motor Insurance Policy Rules"]) and "final decision" in prompt.casefold()
        return ok, {"policy_present": "Motor Insurance Policy Rules" in prompt, "schema_present": "illegal_racing" in prompt, "claim_present": "UNTRUSTED_MARKER" in prompt}, None
    if component == "schema_validation":
        EventExclusionExtraction.model_validate({"event_type":"theft","alcohol_or_drug_involvement":"unknown","illegal_racing":"unknown","intentional_damage":"unknown","outside_permitted_geographic_coverage":"unknown"})
        return True, {"schema_valid": True}, None
    if component == "invalid_schema":
        try:
            EventExclusionExtraction.model_validate({"event_type":"spaceship"})
        except ValidationError:
            return True, {"invalid_rejected": True}, None
        return False, {"invalid_rejected": False}, "Invalid payload was accepted"
    if component == "merge":
        facts = ClaimFacts(event_type="theft", repeated_claims="true", late_submission_valid_reason="false")
        return facts.event_type.value == "theft" and facts.repeated_claims.value == "true", facts.model_dump(mode="json"), None
    if component == "coverage_routing":
        out = analyze_claim(claim, ClaimFacts(event_type="accidental_collision", illegal_racing="true"))
        return out.recommended_routing.value == "Rejection review", out.model_dump(mode="json"), None
    if component == "documents":
        out = analyze_claim(claim, ClaimFacts(event_type="theft"))
        return "police_report" in out.document_check.missing_document_ids, out.model_dump(mode="json"), None
    if component == "risk_routing":
        out = analyze_claim(claim, ClaimFacts(event_type="accidental_collision", severe_damage="true", weak_evidence="true"))
        return out.recommended_routing.value == "Fraud review", out.model_dump(mode="json"), None
    if component == "human_boundary":
        review = TriageService(_Extractor()).prepare_claim(claim)
        try:
            TriageService(_Extractor()).confirm_and_analyze(review, {"claim_id": claim.claim_id, "facts": {}, "confirmed_by_human": False})
        except ValidationError:
            return True, {"unconfirmed_rejected": True}, None
        return False, {"unconfirmed_rejected": False}, "Unconfirmed facts crossed boundary"
    if component == "provider_fallback":
        review = TriageService(_Extractor(fail=True)).prepare_claim(claim)
        ok = not review.proposal.extraction_success and review.proposal.source == "safe_fallback" and review.confirmation_required
        return ok, review.model_dump(mode="json"), None
    if component == "explanation":
        service = TriageService(_Extractor())
        review = service.prepare_claim(claim)
        out = service.confirm_and_analyze(review, ConfirmedClaimFacts(claim_id=claim.claim_id, facts=ClaimFacts(event_type="accidental_collision"), confirmed_by_human=True))
        ok = "not a final claim decision" in out.recommendation_disclaimer
        return ok, {"disclaimer": out.recommendation_disclaimer}, None
    return False, {}, "Unknown component"


def evaluate_components(dataset: EvaluationDataset) -> EvaluationReport:
    results = []
    for case in dataset.cases:
        started = time.perf_counter()
        try:
            ok, actual, reason = _run(case["component"])
        except Exception as exc:
            ok, actual, reason = False, {}, f"{type(exc).__name__}: {exc}"
        results.append(CaseResult(case_id=case["case_id"], scenario=case["scenario"], status="PASS" if ok else "FAIL", expected_result={"component": case["component"], "pass": True}, actual_result=actual, failure_category=None if ok else case["component"], failure_reason=reason, safety_critical=case["safety_critical"], latency_ms=(time.perf_counter()-started)*1000))
    metrics = {**summarize_results(results), "passed_components": sum(r.status == "PASS" for r in results), "failed_components": sum(r.status == "FAIL" for r in results), "safety_critical_pass_rate": ratio(sum(r.status == "PASS" for r in results if r.safety_critical), sum(r.safety_critical for r in results))}
    gates = {"all_components_pass": all(r.status == "PASS" for r in results), "safety_critical_100_percent": all(r.status == "PASS" for r in results if r.safety_critical), "retrieval_evaluation_not_fabricated": True}
    return EvaluationReport(evaluation_level="component", mode="fixture", dataset_version=dataset.dataset_version, model_provider="fixture", prompt_version=PROMPT_VERSION, policy_version=POLICY_VERSION, results=results, metrics=metrics, quality_gates=gates, overall_status="PASS" if all(gates.values()) else "FAIL")
