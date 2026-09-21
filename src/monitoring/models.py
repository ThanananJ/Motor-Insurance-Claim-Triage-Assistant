"""Strict monitoring contracts containing categories and counts, never claim text."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    REQUEST_STARTED = "REQUEST_STARTED"
    AI_EXTRACTION_STARTED = "AI_EXTRACTION_STARTED"
    AI_EXTRACTION_COMPLETED = "AI_EXTRACTION_COMPLETED"
    AI_EXTRACTION_FAILED = "AI_EXTRACTION_FAILED"
    LLM_PROMPT_PREPARED = "LLM_PROMPT_PREPARED"
    LLM_PROMPT_COMPLETED = "LLM_PROMPT_COMPLETED"
    LLM_PROMPT_FAILED = "LLM_PROMPT_FAILED"
    SCHEMA_VALIDATION_COMPLETED = "SCHEMA_VALIDATION_COMPLETED"
    FALLBACK_TRIGGERED = "FALLBACK_TRIGGERED"
    HUMAN_CONFIRMATION_COMPLETED = "HUMAN_CONFIRMATION_COMPLETED"
    HUMAN_OVERRIDE_RECORDED = "HUMAN_OVERRIDE_RECORDED"
    TRIAGE_COMPLETED = "TRIAGE_COMPLETED"
    HUMAN_FINAL_DECISION_RECORDED = "HUMAN_FINAL_DECISION_RECORDED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    REQUEST_FAILED = "REQUEST_FAILED"


class MonitoringEvent(BaseModel):
    """Allow-listed event payload; unknown/PII-shaped fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    environment: str = "local"
    is_synthetic: bool = False
    app_version: str = "0.1.0"
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str = "focused-v1"
    policy_version: str = "5.1"
    output_strategy: str = "current"
    status: str | None = None
    stage: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    provider_status: str | None = None
    provider_error_category: str | None = None
    schema_valid: bool | None = None
    validation_error_category: str | None = None
    fallback_triggered: bool = False
    fallback_reason: str | None = None
    retry_count: int = Field(default=0, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    token_usage_available: bool = False
    prompt_name: str | None = None
    tokenizer_name: str | None = None
    token_count_source: str | None = None
    token_count_available: bool = False
    prompt_token_count: int | None = Field(default=None, ge=0)
    token_count_error_category: str | None = None
    model_capability_context_tokens: int | None = Field(default=None, ge=1)
    effective_context_window_tokens: int | None = Field(default=None, ge=1)
    reserved_output_tokens: int | None = Field(default=None, ge=0)
    max_prompt_tokens: int | None = Field(default=None, ge=1)
    remaining_prompt_capacity_tokens: int | None = None
    context_usage_percent: float | None = Field(default=None, ge=0)
    context_status: Literal["HEALTHY", "WARNING", "CRITICAL", "OVER_LIMIT", "UNKNOWN"] | None = None
    over_prompt_limit: bool | None = None
    context_source: str | None = None
    claim_scenario_category: str | None = None
    ai_facts_proposed_count: int | None = Field(default=None, ge=0)
    ai_unknown_count: int | None = Field(default=None, ge=0)
    human_confirmed: bool = False
    human_override: bool = False
    override_field_count: int = Field(default=0, ge=0)
    changed_field_categories: str | None = None
    override_reason_category: Literal[
        "AI_MISSED_FACT", "AI_UNSUPPORTED_FACT", "AMBIGUOUS_INPUT", "NEW_EVIDENCE",
        "OFFICER_JUDGMENT", "PROVIDER_FAILURE", "OTHER_WITHOUT_FREE_TEXT",
    ] | None = None
    coverage_status: str | None = None
    route: str | None = None
    missing_document_count: int | None = Field(default=None, ge=0)
    risk_signal_count: int | None = Field(default=None, ge=0)
    late_submission_flag: bool | None = None
    human_final_decision_recorded: bool = False
    human_final_decision_category: str = "not_available"

    @field_validator("timestamp_utc")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        return value.astimezone(timezone.utc)


class MonitoringFilter(BaseModel):
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    environment: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    prompt_name: str | None = None
    request_id_prefix: str | None = None
    status: str | None = None
    error_category: str | None = None
    scenario_category: str | None = None
    route: str | None = None
    coverage_status: str | None = None
    synthetic: bool | None = None
