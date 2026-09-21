"""Aggregate runtime events into technical and management indicators."""

from __future__ import annotations

import math
from collections import Counter

from .health import classify_health


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def summarize(events: list[dict]) -> dict:
    starts = {event["request_id"] for event in events if event["event_type"] == "REQUEST_STARTED"}
    completed = {event["request_id"] for event in events if event["event_type"] == "REQUEST_COMPLETED"}
    failed = {event["request_id"] for event in events if event["event_type"] == "REQUEST_FAILED"}
    extractions = [event for event in events if event["event_type"] in {"AI_EXTRACTION_COMPLETED", "AI_EXTRACTION_FAILED"}]
    validations = [event for event in events if event["event_type"] == "SCHEMA_VALIDATION_COMPLETED"]
    fallbacks = {event["request_id"] for event in events if event["event_type"] == "FALLBACK_TRIGGERED"}
    overrides = {event["request_id"] for event in events if event["event_type"] == "HUMAN_OVERRIDE_RECORDED"}
    triage = [event for event in events if event["event_type"] == "TRIAGE_COMPLETED"]
    latencies = [event["latency_ms"] for event in events if event["latency_ms"] is not None]
    prompt_events = [event for event in events if event["event_type"] == "LLM_PROMPT_PREPARED"]
    available_prompts = [event for event in prompt_events if event.get("prompt_token_count") is not None]
    tokens_by_request: dict[str, int] = {}
    for event in available_prompts:
        tokens_by_request[event["request_id"]] = tokens_by_request.get(event["request_id"], 0) + event["prompt_token_count"]
    claim_token_totals = list(tokens_by_request.values())
    context_usages = [event["context_usage_percent"] for event in available_prompts if event.get("context_usage_percent") is not None]
    context_statuses = Counter(event.get("context_status") or "UNKNOWN" for event in prompt_events)
    metrics = {
        "total_requests": len(starts), "completed_requests": len(completed), "failed_requests": len(failed),
        "provider_success_rate": _rate(sum(e["event_type"] == "AI_EXTRACTION_COMPLETED" for e in extractions), len(extractions)),
        "provider_error_count": sum(e["event_type"] == "AI_EXTRACTION_FAILED" for e in extractions),
        "schema_validity_rate": _rate(sum(bool(e["schema_valid"]) for e in validations), len(validations)),
        "fallback_rate": _rate(len(fallbacks), len(starts)),
        "average_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "p95_latency_ms": _p95(latencies),
        "workflow_failure_rate": _rate(len(failed), len(starts)),
        "human_override_rate": _rate(len(overrides), len(completed)),
        "route_distribution": dict(Counter(e["route"] for e in triage if e["route"])),
        "coverage_distribution": dict(Counter(e["coverage_status"] for e in triage if e["coverage_status"])),
        "missing_document_case_rate": _rate(sum((e["missing_document_count"] or 0) > 0 for e in triage), len(triage)),
        "risk_signal_case_rate": _rate(sum((e["risk_signal_count"] or 0) > 0 for e in triage), len(triage)),
        "error_distribution": dict(Counter(e["provider_error_category"] for e in events if e["provider_error_category"])),
        "validation_failure_distribution": dict(Counter(e["validation_error_category"] for e in events if e["validation_error_category"])),
        "fallback_reason_distribution": dict(Counter(e["fallback_reason"] for e in events if e["fallback_reason"])),
        "override_reason_distribution": dict(Counter(e["override_reason_category"] for e in events if e["override_reason_category"])),
        "average_prompt_tokens_per_claim": sum(claim_token_totals) / len(claim_token_totals) if claim_token_totals else None,
        "p95_prompt_tokens_per_claim": _p95(claim_token_totals),
        "maximum_prompt_tokens_observed": max((e["prompt_token_count"] for e in available_prompts), default=None),
        "average_context_usage_percent": sum(context_usages) / len(context_usages) if context_usages else None,
        "highest_context_usage_percent": max(context_usages, default=None),
        "context_status_distribution": dict(context_statuses),
        "token_count_unavailable_rate": _rate(len(prompt_events) - len(available_prompts), len(prompt_events)),
    }
    metrics["health_status"] = classify_health(metrics)
    return metrics
