"""Explicitly seed privacy-safe synthetic monitoring data for dashboard demos."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.monitoring.models import EventType
from src.monitoring.service import MonitoringService


SCENARIOS = [
    ("successful", True, None, "Standard processing", "Likely covered", False, False, 0, 0),
    ("provider_timeout", False, "PROVIDER_TIMEOUT", "Manual review", "Cannot determine", True, False, 2, 0),
    ("schema_failure", False, "SCHEMA_VALIDATION_FAILURE", "Manual review", "Cannot determine", True, False, 1, 0),
    ("human_override", True, None, "Fraud review", "Possibly covered", False, True, 0, 2),
    ("rejection_review", True, None, "Rejection review", "Not covered", False, False, 0, 1),
]


def seed() -> int:
    service = MonitoringService()
    now = datetime.now(timezone.utc)
    count = 0
    for index, (scenario, success, error, route, coverage, fallback, override, missing, risks) in enumerate(SCENARIOS):
        request_id = service.new_request_id()
        common = {"is_synthetic": True, "claim_scenario_category": scenario, "timestamp_utc": now - timedelta(hours=index)}
        count += service.record(EventType.REQUEST_STARTED, request_id, status="started", stage="request", **common)
        count += service.record(EventType.AI_EXTRACTION_STARTED, request_id, status="started", stage="ai_extraction", **common)
        count += service.record(
            EventType.AI_EXTRACTION_COMPLETED if success else EventType.AI_EXTRACTION_FAILED,
            request_id, status="success" if success else "failed", stage="ai_extraction",
            latency_ms=800 + index * 7500, provider_status="success" if success else "failed",
            provider_error_category=error, model_provider="ollama", model_name="qwen2.5:3b", **common,
        )
        count += service.record(
            EventType.SCHEMA_VALIDATION_COMPLETED, request_id, status="passed" if success else "failed",
            stage="validation", schema_valid=success,
            validation_error_category=None if success else "INVALID_OR_UNAVAILABLE_OUTPUT", **common,
        )
        if fallback:
            count += service.record(EventType.FALLBACK_TRIGGERED, request_id, status="safe_fallback", stage="fallback", fallback_triggered=True, fallback_reason="AI_EXTRACTION_UNAVAILABLE", **common)
        count += service.record(EventType.HUMAN_CONFIRMATION_COMPLETED, request_id, status="confirmed", stage="human_confirmation", human_confirmed=True, human_override=override, override_field_count=int(override), **common)
        if override:
            count += service.record(EventType.HUMAN_OVERRIDE_RECORDED, request_id, status="recorded", stage="human_confirmation", human_confirmed=True, human_override=True, override_field_count=1, changed_field_categories="event_type", override_reason_category="NEW_EVIDENCE", **common)
        count += service.record(EventType.TRIAGE_COMPLETED, request_id, status="completed", stage="triage", route=route, coverage_status=coverage, missing_document_count=missing, risk_signal_count=risks, **common)
        count += service.record(EventType.REQUEST_COMPLETED, request_id, status="completed", stage="request", human_confirmed=True, **common)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear-synthetic", action="store_true", help="delete only synthetic rows")
    parser.add_argument("--yes", action="store_true", help="confirm synthetic-row deletion")
    args = parser.parse_args()
    service = MonitoringService()
    if args.clear_synthetic:
        if not args.yes:
            parser.error("--clear-synthetic requires explicit --yes")
        print(f"Deleted {service.repository.delete_synthetic()} synthetic monitoring events.")
    else:
        print(f"Inserted {seed()} synthetic monitoring events.")


if __name__ == "__main__":
    main()
