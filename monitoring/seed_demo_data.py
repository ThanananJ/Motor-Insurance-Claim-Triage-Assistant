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

PROMPTS = ("focused-event-exclusion", "focused-history-risk", "focused-late-reason")
TOKEN_CASES = (
    ("HEALTHY", 920),
    ("WARNING", 24000),
    ("CRITICAL", 29000),
    ("OVER_LIMIT", 33000),
    ("UNKNOWN", None),
)


def seed() -> int:
    service = MonitoringService()
    now = datetime.now(timezone.utc)
    count = 0
    for index, (scenario, success, error, route, coverage, fallback, override, missing, risks) in enumerate(SCENARIOS):
        request_id = service.new_request_id()
        common = {"is_synthetic": True, "claim_scenario_category": scenario, "timestamp_utc": now - timedelta(hours=index)}
        count += service.record(EventType.REQUEST_STARTED, request_id, status="started", stage="request", **common)
        count += service.record(EventType.AI_EXTRACTION_STARTED, request_id, status="started", stage="ai_extraction", **common)
        context_status, base_tokens = TOKEN_CASES[index]
        for prompt_index, prompt_name in enumerate(PROMPTS):
            prompt_tokens = None if base_tokens is None else base_tokens + prompt_index * 25
            maximum = 32512
            count += service.record(
                EventType.LLM_PROMPT_PREPARED, request_id,
                status=context_status, stage="prompt_preflight", prompt_name=prompt_name,
                model_provider="ollama", model_name="qwen2.5:3b",
                tokenizer_name="Qwen/Qwen2.5-3B-Instruct",
                token_count_source="qwen_chat_template",
                token_count_available=prompt_tokens is not None,
                prompt_token_count=prompt_tokens,
                token_count_error_category=None if prompt_tokens is not None else "TOKENIZER_UNAVAILABLE",
                model_capability_context_tokens=131072,
                effective_context_window_tokens=32768,
                reserved_output_tokens=256,
                max_prompt_tokens=maximum,
                remaining_prompt_capacity_tokens=None if prompt_tokens is None else maximum - prompt_tokens,
                context_usage_percent=None if prompt_tokens is None else prompt_tokens / maximum * 100,
                context_status=context_status,
                over_prompt_limit=None if prompt_tokens is None else prompt_tokens > maximum,
                context_source="application_num_ctx", provider_status="not_called", **common,
            )
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
