"""Dataset/report I/O with deliberately redacted structured audit logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.schemas import EvaluationDataset, EvaluationReport

ROOT = Path(__file__).parents[1]
DATASETS = Path(__file__).parent / "datasets"
RESULTS = ROOT / "results" / "evaluation"


def load_dataset(level: str) -> EvaluationDataset:
    return EvaluationDataset.model_validate_json((DATASETS / f"{level}_cases.json").read_text(encoding="utf-8"))


def write_report(report: EvaluationReport, output_dir: Path | None = None) -> tuple[Path, Path]:
    target = output_dir or RESULTS
    runs = target / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    report_path = runs / f"{report.evaluation_run_id}-{report.evaluation_level}.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    latest = target / f"latest-{report.evaluation_level}.json"
    latest.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    log_path = runs / f"{report.evaluation_run_id}.jsonl"
    with log_path.open("w", encoding="utf-8") as stream:
        for result in report.results:
            record: dict[str, Any] = {
                "evaluation_run_id": report.evaluation_run_id,
                "case_id": result.case_id,
                "timestamp": report.timestamp,
                "evaluation_level": report.evaluation_level,
                "scenario_tags": result.actual_result.get("tags", []),
                "model_provider": report.model_provider,
                "model_name": report.model_name,
                "prompt_name": result.prompt_name,
                "prompt_version": report.prompt_version,
                "policy_version": report.policy_version,
                "latency_ms": result.latency_ms,
                "input_tokens": None,
                "output_tokens": None,
                "token_usage_unavailable": True,
                "structured_output_valid": result.structured_output_valid,
                "schema_validation_passed": result.schema_validation_passed,
                "validation_errors": result.failure_reason,
                "fallback_triggered": result.fallback_triggered,
                "fallback_reason": result.fallback_reason,
                "expected_result": result.expected_result,
                "actual_result": result.actual_result,
                "metric_results": result.metric_results,
                "pass_fail_status": result.status,
                "failure_category": result.failure_category,
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return report_path, log_path
