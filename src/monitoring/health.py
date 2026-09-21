"""Configurable initial operational thresholds (not permanent business standards)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthThresholds:
    provider_warning: float = 0.95
    provider_critical: float = 0.80
    schema_warning: float = 0.95
    schema_critical: float = 0.80
    fallback_warning: float = 0.05
    fallback_critical: float = 0.20
    p95_warning_ms: float = 10_000
    p95_critical_ms: float = 30_000
    failure_warning: float = 0.02
    failure_critical: float = 0.10


def classify_health(metrics: dict, thresholds: HealthThresholds | None = None) -> str:
    thresholds = thresholds or HealthThresholds()
    if not metrics.get("total_requests"):
        return "NO_DATA"
    value = lambda name, default: default if metrics.get(name) is None else metrics[name]
    critical = (
        value("provider_success_rate", 1) < thresholds.provider_critical
        or value("schema_validity_rate", 1) < thresholds.schema_critical
        or value("fallback_rate", 0) > thresholds.fallback_critical
        or value("p95_latency_ms", 0) > thresholds.p95_critical_ms
        or value("workflow_failure_rate", 0) > thresholds.failure_critical
    )
    if critical:
        return "CRITICAL"
    warning = (
        value("provider_success_rate", 1) < thresholds.provider_warning
        or value("schema_validity_rate", 1) < thresholds.schema_warning
        or value("fallback_rate", 0) > thresholds.fallback_warning
        or value("p95_latency_ms", 0) > thresholds.p95_warning_ms
        or value("workflow_failure_rate", 0) > thresholds.failure_warning
    )
    return "WARNING" if warning else "HEALTHY"
