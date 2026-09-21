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
    }
    metrics["health_status"] = classify_health(metrics)
    return metrics
