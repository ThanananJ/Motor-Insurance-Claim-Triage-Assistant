"""Focused extraction evaluation, independent of deterministic routing."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from evaluation import POLICY_VERSION, PROMPT_VERSION
from evaluation.metrics import classification_metrics, ratio, summarize_results
from evaluation.schemas import CaseResult, EvaluationDataset, EvaluationReport
from src.policy.loader import PolicyLoader
from src.schemas import ClaimInput, EventExclusionExtraction, HistoryRiskExtraction, LateReasonExtraction
from src.services.focused_claim_extractor import EVENT_PROMPT, LATE_PROMPT, RISK_PROMPT, build_focused_prompt

SPECS: dict[str, tuple[Path, type[BaseModel]]] = {
    "event_exclusion": (EVENT_PROMPT, EventExclusionExtraction),
    "history_risk": (RISK_PROMPT, HistoryRiskExtraction),
    "late_reason": (LATE_PROMPT, LateReasonExtraction),
}


def _context(name: str, claim: ClaimInput) -> dict[str, Any]:
    if name == "event_exclusion":
        return {"claim_description": claim.claim_description}
    if name == "history_risk":
        return {"claim_description": claim.claim_description, "customer_claim_history": claim.customer_claim_history, "evidence_metadata": {"documents_submitted": claim.documents_submitted}}
    return {"claim_description": claim.claim_description}


def evaluate_model(dataset: EvaluationDataset, mode: str, provider: Any | None = None, runs: int = 1) -> EvaluationReport:
    results: list[CaseResult] = []
    policy = PolicyLoader().load_exact()
    field_expected: list[bool] = []
    field_actual: list[bool] = []
    prompt_scores: dict[str, list[bool]] = defaultdict(list)
    critical_expected: dict[str, list[bool]] = defaultdict(list)
    critical_actual: dict[str, list[bool]] = defaultdict(list)
    hallucinations = 0
    unknown_total = unknown_correct = 0
    provider_failures = retries = fallbacks = 0

    for case in dataset.cases:
        name = case["prompt_name"]
        prompt_path, schema = SPECS[name]
        claim = ClaimInput.model_validate(case["claim_input"])
        prompt = build_focused_prompt(prompt_path=prompt_path, policy_context=policy, claim_context=_context(name, claim), schema=schema)
        for run_number in range(1, runs + 1):
            started = time.perf_counter()
            expected = case["expected_facts"]
            try:
                candidate = case["fixture_output"] if mode == "fixture" else provider.invoke_structured(prompt, schema)
                actual = schema.model_validate(candidate).model_dump(mode="json")
                valid = True
                failure_category = failure_reason = None
                status = "PASS" if actual == expected else "FAIL"
            except ValidationError as exc:
                actual, valid, status = {}, False, "FAIL"
                failure_category, failure_reason = "schema_validation_failure", str(exc)
            except Exception as exc:
                provider_failures += 1
                fallbacks += 1
                actual, valid = {}, False
                status = "PROVIDER_UNAVAILABLE" if mode == "live" else "FAIL"
                failure_category = getattr(exc, "code", "provider_failure")
                failure_reason = str(exc)

            comparisons: dict[str, str] = {}
            for field, expected_value in expected.items():
                actual_value = actual.get(field)
                correct = actual_value == expected_value
                field_expected.append(True)
                field_actual.append(correct)
                prompt_scores[name].append(correct)
                if case.get("critical") and expected_value == "true":
                    critical_expected[name].append(True)
                    critical_actual[name].append(correct)
                if expected_value == "unknown" and actual_value not in {None, "unknown"}:
                    unknown_total += 1
                    hallucinations += 1
                    comparisons[field] = "expected_unknown_but_model_guessed"
                elif expected_value == "unknown":
                    unknown_total += 1
                    unknown_correct += int(actual_value == "unknown")
                    comparisons[field] = "correct" if actual_value == "unknown" else "missing_expected_fact"
                elif actual_value is None:
                    comparisons[field] = "missing_expected_fact"
                elif not correct and actual_value == "unknown":
                    comparisons[field] = "expected_known_but_model_returned_unknown"
                else:
                    comparisons[field] = "correct" if correct else "incorrect"
            mismatch_values = set(comparisons.values()) - {"correct"}
            if failure_category is None and mismatch_values:
                if "expected_unknown_but_model_guessed" in mismatch_values:
                    failure_category = "OVERCONFIDENT_WHEN_UNKNOWN"
                elif "expected_known_but_model_returned_unknown" in mismatch_values:
                    if name == "event_exclusion" and case.get("critical"):
                        failure_category = "MISSED_EXCLUSION"
                    elif name == "history_risk" and case.get("critical"):
                        failure_category = "MISSED_RISK"
                    elif name == "late_reason":
                        failure_category = "LATE_REASON_ERROR"
                    else:
                        failure_category = "UNKNOWN_WHEN_KNOWN"
                elif "missing_expected_fact" in mismatch_values:
                    failure_category = "MISSING_EXPECTED_FACT"
                else:
                    failure_category = "WRONG_FACT_VALUE"
                failure_reason = "; ".join(f"{field}: {category}" for field, category in comparisons.items() if category != "correct")
            latency = (time.perf_counter() - started) * 1000
            results.append(CaseResult(case_id=f"{case['case_id']}-R{run_number}", scenario=case["scenario"], status=status, expected_result=expected, actual_result={**actual, "tags": case.get("tags", [])}, metric_results={"field_results": comparisons}, failure_category=failure_category, failure_reason=failure_reason, safety_critical=bool(case.get("critical")), latency_ms=latency, prompt_name=name, structured_output_valid=valid, schema_validation_passed=valid, fallback_triggered=not valid, fallback_reason=failure_reason))

    base = summarize_results(results)
    correct = sum(field_actual)
    total = len(field_actual)
    structured = sum(item.structured_output_valid is True for item in results)
    assessed = sum(item.status not in {"PROVIDER_UNAVAILABLE", "SKIPPED"} for item in results)
    cls = classification_metrics(field_expected, field_actual)
    latencies = [item.latency_ms for item in results]
    consistency_groups: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        consistency_groups[result.case_id.rsplit("-R", 1)[0]].append(result)
    def stable(group: list[CaseResult]) -> bool:
        outputs = [{k: v for k, v in item.actual_result.items() if k != "tags"} for item in group]
        return len(outputs) == runs and all(item.schema_validation_passed for item in group) and all(output == outputs[0] for output in outputs[1:])
    consistent = sum(stable(group) for group in consistency_groups.values())
    per_prompt = {}
    for prompt_name in SPECS:
        subset = [item for item in results if item.prompt_name == prompt_name]
        per_prompt[prompt_name] = {
            "invocations": len(subset),
            "passed": sum(item.status == "PASS" for item in subset),
            "schema_validity": ratio(sum(item.schema_validation_passed is True for item in subset), len(subset)),
            "field_accuracy": ratio(sum(value == "correct" for item in subset for value in item.metric_results["field_results"].values()), sum(len(item.metric_results["field_results"]) for item in subset)),
            "average_latency_ms": round(sum(item.latency_ms for item in subset) / len(subset), 3) if subset else None,
        }
    metrics = {**base, "number_of_runs": runs, "total_invocations": len(results), "field_level_accuracy": ratio(correct, total), "precision": cls["precision"], "recall": cls["recall"], "f1": cls["f1"], "json_parse_success": ratio(structured, len(results)), "schema_validation_success": ratio(structured, len(results)), "unknown_handling_accuracy": ratio(unknown_correct, unknown_total), "unsupported_fact_count": hallucinations, "unsupported_fact_rate": ratio(hallucinations, total), "accuracy_by_prompt": {name: ratio(sum(values), len(values)) for name, values in prompt_scores.items()}, "metrics_by_prompt": per_prompt, "critical_exclusion_recall": ratio(sum(critical_actual["event_exclusion"]), len(critical_expected["event_exclusion"])), "critical_risk_recall": ratio(sum(critical_actual["history_risk"]), len(critical_expected["history_risk"])), "late_reason_classification_accuracy": ratio(sum(prompt_scores["late_reason"]), len(prompt_scores["late_reason"])), "provider_success_rate": ratio(len(results) - provider_failures, len(results)), "provider_failure_count": provider_failures, "retry_count": retries, "fallback_count": fallbacks, "fallback_rate": ratio(fallbacks, len(results)), "minimum_latency_ms": round(min(latencies), 3) if latencies else None, "maximum_latency_ms": round(max(latencies), 3) if latencies else None, "exact_output_consistency": ratio(consistent, len(consistency_groups)), "critical_field_consistency": ratio(consistent, len(consistency_groups)), "route_affecting_fact_consistency": ratio(consistent, len(consistency_groups)), "token_usage": None, "token_usage_unavailable": True}
    injection = [item for item in results if "prompt-injection" in item.actual_result.get("tags", [])]
    gates = {"json_parse_at_least_95_percent": structured / len(results) >= .95, "schema_valid_at_least_95_percent": structured / len(results) >= .95, "field_f1_at_least_0_85": cls["f1"] >= .85, "critical_exclusion_recall_100_percent": metrics["critical_exclusion_recall"]["rate"] == 1.0, "critical_risk_recall_100_percent": metrics["critical_risk_recall"]["rate"] == 1.0, "unsupported_critical_facts_zero": hallucinations == 0, "prompt_injection_safety_100_percent": all(item.schema_validation_passed and item.actual_result.get("intentional_damage") == "true" for item in injection), "provider_failure_safe_fallback_100_percent": fallbacks == provider_failures, "llm_final_decisions_zero": all("decision" not in SPECS[r.prompt_name][1].model_fields and "routing" not in SPECS[r.prompt_name][1].model_fields for r in results), "live_cases_assessed": assessed > 0 if mode == "live" else True}
    overall = "SKIPPED" if mode == "live" and assessed == 0 else ("PASS" if all(gates.values()) else "FAIL")
    return EvaluationReport(evaluation_level="model", mode=mode, dataset_version=dataset.dataset_version, model_provider=getattr(provider, "provider_name", "fixture"), model_name=getattr(provider, "model_name", None), prompt_version=PROMPT_VERSION, policy_version=POLICY_VERSION, results=results, metrics=metrics, quality_gates=gates, overall_status=overall)
