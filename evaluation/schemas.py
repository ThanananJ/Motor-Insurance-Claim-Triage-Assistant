"""Strict contracts for datasets, case results, and audit records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class EvaluationDataset(BaseModel):
    dataset_version: str
    evaluation_level: Literal["model", "component", "e2e"]
    cases: list[dict[str, Any]]


class CaseResult(BaseModel):
    case_id: str
    scenario: str
    status: Literal["PASS", "PARTIAL", "FAIL", "SKIPPED", "PROVIDER_UNAVAILABLE"]
    expected_result: dict[str, Any] = Field(default_factory=dict)
    actual_result: dict[str, Any] = Field(default_factory=dict)
    metric_results: dict[str, Any] = Field(default_factory=dict)
    failure_category: str | None = None
    failure_reason: str | None = None
    safety_critical: bool = False
    latency_ms: float = 0.0
    prompt_name: str | None = None
    structured_output_valid: bool | None = None
    schema_validation_passed: bool | None = None
    retry_count: int = 0
    fallback_triggered: bool = False
    fallback_reason: str | None = None


class EvaluationReport(BaseModel):
    evaluation_run_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluation_level: Literal["model", "component", "e2e"]
    mode: str
    dataset_version: str
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str
    policy_version: str
    retrieval_evaluation: str = "Not Applicable in Current Implementation"
    results: list[CaseResult]
    metrics: dict[str, Any]
    quality_gates: dict[str, Any]
    overall_status: Literal["PASS", "PARTIAL", "FAIL", "SKIPPED"]
