"""Transparent metric helpers; percentages always retain their counts."""

from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any

from evaluation.schemas import CaseResult


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": round(numerator / denominator, 4) if denominator else None,
    }


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percent)))
    return round(ordered[index], 3)


def summarize_results(results: list[CaseResult]) -> dict[str, Any]:
    counts = Counter(item.status for item in results)
    assessed = [item for item in results if item.status not in {"SKIPPED", "PROVIDER_UNAVAILABLE"}]
    passed = sum(item.status == "PASS" for item in assessed)
    latencies = [item.latency_ms for item in results if item.latency_ms >= 0]
    return {
        "total_cases": len(results),
        "status_counts": dict(counts),
        "pass_rate": ratio(passed, len(assessed)),
        "average_latency_ms": round(mean(latencies), 3) if latencies else None,
        "p50_latency_ms": round(median(latencies), 3) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95),
    }


def classification_metrics(expected: list[bool], actual: list[bool]) -> dict[str, Any]:
    tp = sum(e and a for e, a in zip(expected, actual))
    fp = sum(not e and a for e, a in zip(expected, actual))
    fn = sum(e and not a for e, a in zip(expected, actual))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}
