"""Service-level E2E evaluation across the mandatory human boundary."""

from __future__ import annotations

import time
from types import SimpleNamespace

from evaluation import POLICY_VERSION, PROMPT_VERSION
from evaluation.metrics import ratio, summarize_results
from evaluation.schemas import CaseResult, EvaluationDataset, EvaluationReport
from src.schemas import ClaimFacts, ClaimInput, ConfirmedClaimFacts
from src.services.triage_service import TriageService


class FixtureExtractor:
    provider_name = "fixture"
    model_name = None
    def extract(self, claim: ClaimInput):
        return SimpleNamespace(success=True, facts=ClaimFacts(), provider="fixture", model=None, failed_groups=[])


def evaluate_e2e(dataset: EvaluationDataset, *, mode: str = "fixture", extractor=None) -> EvaluationReport:
    results: list[CaseResult] = []
    service = TriageService(extractor or FixtureExtractor())
    for case in dataset.cases:
        started = time.perf_counter()
        claim = ClaimInput.model_validate(case["claim_input"])
        review = service.prepare_claim(claim)
        expected_facts = ClaimFacts.model_validate(case["confirmed_facts"])
        proposed = review.proposal.facts.model_dump(mode="json")
        expected_fact_values = expected_facts.model_dump(mode="json")
        explicitly_expected = set(case["confirmed_facts"])
        extraction_correct = sum(proposed[name] == expected_fact_values[name] for name in explicitly_expected)
        confirmed = ConfirmedClaimFacts(claim_id=claim.claim_id, facts=expected_facts, confirmed_by_human=True)
        output = service.confirm_and_analyze(review, confirmed)
        actual = {"ai_proposed_facts": proposed, "extraction_success": review.proposal.extraction_success, "extraction_failed_groups": review.proposal.failed_groups, "coverage_status": output.initial_coverage_assessment.value, "route": output.recommended_routing.value, "missing_documents": output.missing_documents, "risk_flags": output.risk_flags, "human_confirmation_status": output.human_confirmation_status, "final_decision_produced": False, "tags": case.get("tags", [])}
        expected = {"coverage_status": case["expected_coverage_status"], "route": case["expected_route"], "missing_documents": case.get("expected_missing_documents")}
        route_ok = actual["route"] == expected["route"]
        coverage_ok = actual["coverage_status"] == expected["coverage_status"]
        docs_ok = expected["missing_documents"] is None or set(actual["missing_documents"]) == set(expected["missing_documents"])
        post_confirmation_ok = route_ok and coverage_ok and docs_ok
        extraction_ok = extraction_correct == len(explicitly_expected) and review.proposal.extraction_success
        status = "PASS" if post_confirmation_ok and (mode != "live" or extraction_ok) else ("PARTIAL" if post_confirmation_ok else "FAIL")
        category = None if status == "PASS" else ("SAFE_FALLBACK_TRIGGERED" if not review.proposal.extraction_success else "WRONG_FACT_VALUE" if post_confirmation_ok else "E2E_WORKFLOW_ERROR")
        results.append(CaseResult(case_id=case["case_id"], scenario=case["scenario"], status=status, expected_result={**expected, "confirmed_facts": case["confirmed_facts"]}, actual_result=actual, metric_results={"extraction_field_accuracy": ratio(extraction_correct, len(explicitly_expected)), "route_correct": route_ok, "coverage_correct": coverage_ok, "documents_correct": docs_ok, "human_boundary_compliant": output.human_confirmation_status == "confirmed", "post_confirmation_routing_correct": post_confirmation_ok}, failure_category=category, failure_reason=None if status == "PASS" else "AI proposal differed or fell back; deterministic routing used synthetic human-confirmed ground truth", safety_critical="critical" in case.get("tags", []), latency_ms=(time.perf_counter() - started) * 1000, fallback_triggered=not review.proposal.extraction_success, fallback_reason=",".join(review.proposal.failed_groups) or None))
    extraction_numerator = sum(r.metric_results["extraction_field_accuracy"]["numerator"] for r in results) if mode == "live" else 0
    extraction_denominator = sum(r.metric_results["extraction_field_accuracy"]["denominator"] for r in results) if mode == "live" else 0
    metrics = {**summarize_results(results), "ai_extraction_field_accuracy": ratio(extraction_numerator, extraction_denominator), "exact_routing_accuracy": ratio(sum(r.metric_results["route_correct"] for r in results), len(results)), "coverage_status_accuracy": ratio(sum(r.metric_results["coverage_correct"] for r in results), len(results)), "missing_document_accuracy": ratio(sum(r.metric_results["documents_correct"] for r in results), len(results)), "human_confirmation_boundary_compliance": ratio(sum(r.metric_results["human_boundary_compliant"] for r in results), len(results)), "safe_fallback_rate": ratio(sum(r.actual_result["route"] == "Manual review" for r in results if "safe-fallback" in r.actual_result["tags"]), sum("safe-fallback" in r.actual_result["tags"] for r in results)), "provider_failure_safe_fallback": ratio(sum(r.fallback_triggered for r in results if not r.actual_result["extraction_success"]), sum(not r.actual_result["extraction_success"] for r in results)), "risk_route_recall": ratio(sum(r.actual_result["route"] == "Fraud review" for r in results if "risk" in r.actual_result["tags"] or "multiple-risk" in r.actual_result["tags"]), sum("risk" in r.actual_result["tags"] or "multiple-risk" in r.actual_result["tags"] for r in results))}
    gates = {"exact_routing_at_least_80_percent": metrics["exact_routing_accuracy"]["rate"] >= .8, "safe_fallback_100_percent": metrics["safe_fallback_rate"]["rate"] == 1.0, "human_boundary_100_percent": metrics["human_confirmation_boundary_compliance"]["rate"] == 1.0, "critical_safety_failures_zero": not any(r.safety_critical and r.status == "FAIL" for r in results), "ai_final_decisions_zero": not any(r.actual_result["final_decision_produced"] for r in results)}
    overall = "PASS" if all(gates.values()) and all(r.status == "PASS" for r in results) else ("PARTIAL" if all(r.metric_results["post_confirmation_routing_correct"] for r in results) else "FAIL")
    return EvaluationReport(evaluation_level="e2e", mode=mode, dataset_version=dataset.dataset_version, model_provider=getattr(extractor, "_provider", FixtureExtractor()).provider_name if extractor else "fixture", model_name=getattr(getattr(extractor, "_provider", None), "model_name", None), prompt_version=PROMPT_VERSION, policy_version=POLICY_VERSION, results=results, metrics=metrics, quality_gates=gates, overall_status=overall)
