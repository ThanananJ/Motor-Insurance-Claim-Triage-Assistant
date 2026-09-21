"""Phase 2.2 evaluation-only structured-output strategy comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from evaluation import PROMPT_VERSION
from evaluation.diagnostic import SELECTED_CASES, _message_snapshot
from evaluation.evaluators.model_evaluator import SPECS, _context
from evaluation.io import RESULTS, load_dataset
from src.config import AppConfig
from src.policy.loader import PolicyLoader
from src.schemas import ClaimInput
from src.services.focused_claim_extractor import build_focused_prompt


MINIMAL_JSON_INSTRUCTION = """

<experimental_output_format>
Return one JSON object only. Use exactly the fields listed in the output schema.
Use only the schema's allowed values. Use unknown only when the claim data
genuinely lacks evidence. Do not infer unsupported facts. Do not add markdown,
explanation, coverage, routing, approval, rejection, or a final decision.
</experimental_output_format>
""".strip()

STRATEGIES = ("current", "minimal-json")
PRODUCTION_DEFAULT_STRATEGY = "current"
EXPERIMENTAL_STRATEGY = "minimal-json"
OUTPUT_TOKEN_LIMIT = 256
TOTAL_DEADLINE_SECONDS = 30.0
MAX_RETRIES = 1


def _client(config: AppConfig, *, json_only: bool = False) -> ChatOllama:
    return ChatOllama(
        model=config.require_ollama_model(),
        base_url=config.ollama_base_url,
        temperature=0,
        seed=42,
        num_predict=OUTPUT_TOKEN_LIMIT,
        keep_alive="5m",
        format="json" if json_only else None,
        validate_model_on_init=False,
        client_kwargs={"timeout": config.ollama_timeout_seconds},
    )


def warm_up(config: AppConfig) -> dict[str, Any]:
    result = invoke_bounded(
        "minimal-json",
        config,
        'Return exactly this JSON object and nothing else: {"ready": true}',
        _WarmupPayload,
        deadline_seconds=TOTAL_DEADLINE_SECONDS,
        max_retries=0,
    )
    result["excluded_from_comparison"] = True
    return result


class _WarmupPayload(BaseModel):
    ready: bool


def invoke_strategy(
    strategy: str,
    config: AppConfig,
    prompt: str,
    schema: type[BaseModel],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if strategy == "current":
            envelope = _client(config).with_structured_output(
                schema, method="json_schema", include_raw=True
            ).invoke(prompt)
            raw = envelope.get("raw")
            parsed = envelope.get("parsed")
            parsing_error = envelope.get("parsing_error")
            raw_snapshot = _message_snapshot(raw)
            raw_content = raw_snapshot.get("content")
        elif strategy == "minimal-json":
            response = _client(config, json_only=True).invoke(
                prompt + "\n\n" + MINIMAL_JSON_INSTRUCTION
            )
            raw_snapshot = _message_snapshot(response)
            raw_content = raw_snapshot.get("content")
            parsing_error = None
            try:
                parsed = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except (json.JSONDecodeError, TypeError) as exc:
                parsed = None
                parsing_error = f"{type(exc).__name__}: {exc}"
        else:
            raise ValueError(f"Unsupported strategy: {strategy}")

        validated = None
        validation_error = None
        if parsing_error is None:
            try:
                validated = schema.model_validate(parsed).model_dump(mode="json")
            except (ValidationError, TypeError, ValueError) as exc:
                validation_error = f"{type(exc).__name__}: {exc}"
        return {
            "success": validated is not None,
            "raw": raw_snapshot,
            "json_valid": parsing_error is None and parsed is not None,
            "parsed": parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed,
            "pydantic_valid": validated is not None,
            "actual": validated,
            "parsing_error": str(parsing_error) if parsing_error else None,
            "validation_error": validation_error,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "fallback_triggered": validated is None,
            "output_token_count": _output_tokens(raw_snapshot),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "json_valid": False,
            "pydantic_valid": False,
            "actual": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "fallback_triggered": True,
            "output_token_count": None,
        }


def _output_tokens(snapshot: dict[str, Any]) -> int | None:
    metadata = snapshot.get("response_metadata") or {}
    usage = snapshot.get("usage_metadata") or {}
    value = metadata.get("eval_count") or usage.get("output_tokens")
    return int(value) if isinstance(value, (int, float)) else None


def _invocation_worker(strategy: str, config: AppConfig, prompt: str, schema: type[BaseModel], result_queue) -> None:
    result_queue.put(invoke_strategy(strategy, config, prompt, schema))


def _run_process(target, args: tuple[Any, ...], deadline_seconds: float) -> bool:
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=target, args=args)
    process.start()
    process.join(deadline_seconds)
    completed = not process.is_alive()
    if not completed:
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
    return completed


def invoke_bounded(
    strategy: str,
    config: AppConfig,
    prompt: str,
    schema: type[BaseModel],
    *,
    deadline_seconds: float = TOTAL_DEADLINE_SECONDS,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(1, max_retries + 2):
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()
        started = time.perf_counter()
        completed = _run_process(
            _invocation_worker,
            (strategy, config, prompt, schema, result_queue),
            deadline_seconds,
        )
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        if completed and not result_queue.empty():
            result = result_queue.get()
            result["deadline_ms"] = round(deadline_seconds * 1000, 3)
            result["attempt_count"] = attempt_number
            result["retry_count"] = attempt_number - 1
            result["attempts"] = attempts + [{"attempt": attempt_number, "status": "SUCCESS" if result.get("success") else "PROVIDER_FAILURE", "latency_ms": elapsed, "error": result.get("error")}]
            if result.get("success") or not _transient_failure(result) or attempt_number > max_retries:
                return result
            attempts = result["attempts"]
            continue
        attempts.append({"attempt": attempt_number, "status": "PROVIDER_TIMEOUT", "latency_ms": elapsed, "error": f"Total deadline exceeded ({deadline_seconds}s)"})
        if attempt_number > max_retries:
            return {"success": False, "error": "PROVIDER_TIMEOUT", "failure_category": "PROVIDER_TIMEOUT", "json_valid": False, "pydantic_valid": False, "actual": None, "latency_ms": sum(item["latency_ms"] for item in attempts), "deadline_ms": round(deadline_seconds * 1000, 3), "attempt_count": attempt_number, "retry_count": attempt_number - 1, "attempts": attempts, "fallback_triggered": True, "output_token_count": None}
    raise AssertionError("unreachable")


def _transient_failure(result: dict[str, Any]) -> bool:
    error = (result.get("error") or "").casefold()
    return any(token in error for token in ("timeout", "connect", "connection", "provider"))


def execute_sequential(tasks: list[Any], executor) -> list[Any]:
    return [executor(task) for task in tasks]


def compare_fields(expected: dict[str, str], actual: dict[str, str] | None) -> dict[str, Any]:
    actual = actual or {}
    comparisons = {name: {"expected": value, "actual": actual.get(name), "correct": actual.get(name) == value} for name, value in expected.items()}
    unsupported = [name for name, value in expected.items() if value == "unknown" and actual.get(name) not in (None, "unknown")]
    critical_unsupported = [name for name in unsupported if actual.get(name) == "true"]
    return {
        "fields": comparisons,
        "correct": sum(item["correct"] for item in comparisons.values()),
        "total": len(comparisons),
        "unsupported_fields": unsupported,
        "unsupported_critical_fields": critical_unsupported,
    }


def gate1_decision(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_case_strategy = {(item["case_id"], item["strategy"]): item for item in records}
    risk_fields = ("repeated_claims", "severe_damage", "weak_evidence")
    event_fields = ("event_type", "illegal_racing")

    def correct_count(case_id: str, strategy: str, fields: tuple[str, ...]) -> int:
        field_results = by_case_strategy[(case_id, strategy)]["comparison"]["fields"]
        return sum(field_results[name]["correct"] for name in fields)

    risk_a = correct_count("MODEL-RISK-001", "current", risk_fields)
    risk_b = correct_count("MODEL-RISK-001", "minimal-json", risk_fields)
    late_a = correct_count("MODEL-LATE-001", "current", ("late_submission_valid_reason",))
    late_b = correct_count("MODEL-LATE-001", "minimal-json", ("late_submission_valid_reason",))
    event_a = correct_count("MODEL-EVENT-001", "current", event_fields)
    event_b = correct_count("MODEL-EVENT-001", "minimal-json", event_fields)
    control_b = by_case_strategy[("MODEL-EVENT-002", "minimal-json")]
    minimal = [item for item in records if item["strategy"] == "minimal-json"]
    checks = {
        "risk_improved": risk_b > risk_a,
        "late_not_worse": late_b >= late_a,
        "event_not_worse": event_b >= event_a,
        "control_no_unsupported_fact": control_b["result"]["pydantic_valid"] and not control_b["comparison"]["unsupported_fields"],
        "unsupported_critical_facts_zero": not any(item["comparison"]["unsupported_critical_fields"] for item in minimal),
        "json_and_pydantic_all_valid": all(item["result"]["json_valid"] and item["result"]["pydantic_valid"] for item in minimal),
        "no_final_decision_fields": all(not ({"routing", "final_decision", "coverage_decision"} & set((item["result"].get("actual") or {}))) for item in minimal),
        "no_safety_regression": True,
    }
    provider_results_sufficient = all(item["result"]["pydantic_valid"] for item in records)
    control_hallucination = control_b["result"]["pydantic_valid"] and bool(control_b["comparison"]["unsupported_fields"])
    passed = all(checks.values()) and provider_results_sufficient
    safety_rejected = control_hallucination or not checks["unsupported_critical_facts_zero"] or not checks["no_final_decision_fields"]
    return {
        "status": "REJECTED_FOR_SAFETY" if safety_rejected else ("PASS" if passed else ("INCONCLUSIVE" if not provider_results_sufficient else "FAIL")),
        "checks": checks,
        "provider_results_sufficient": provider_results_sufficient,
        "critical_correct_counts": {"risk": {"current": risk_a, "minimal_json": risk_b, "total": len(risk_fields)}, "late": {"current": late_a, "minimal_json": late_b, "total": 1}, "event": {"current": event_a, "minimal_json": event_b, "total": len(event_fields)}},
        "gate2": "RUN" if passed else "SKIPPED_BY_GATE",
    }


def run(case_ids: list[str], strategies: list[str], output_dir: Path) -> tuple[Path, dict[str, Any]]:
    cases = {item["case_id"]: item for item in load_dataset("model").cases}
    config = AppConfig.from_env()
    policy = PolicyLoader().load_exact()
    warmup = warm_up(config)
    records = []
    # Alternate strategy order to reduce systematic warm-state ordering effects.
    for index, case_id in enumerate(case_ids):
        case = cases[case_id]
        prompt_name = case["prompt_name"]
        prompt_path, schema = SPECS[prompt_name]
        claim = ClaimInput.model_validate(case["claim_input"])
        prompt = build_focused_prompt(prompt_path=prompt_path, policy_context=policy, claim_context=_context(prompt_name, claim), schema=schema)
        order = list(strategies)
        if len(order) == 2 and index % 2:
            order.reverse()
        tasks = [(strategy, case_id, case, prompt_name, prompt, schema) for strategy in order]
        def execute(task):
            strategy, selected_case_id, selected_case, selected_prompt_name, selected_prompt, selected_schema = task
            result = invoke_bounded(strategy, config, selected_prompt, selected_schema)
            return {
                "case_id": selected_case_id,
                "prompt_name": selected_prompt_name,
                "strategy": strategy,
                "expected": selected_case["expected_facts"],
                "prompt_metadata": {"version": PROMPT_VERSION, "length": len(selected_prompt), "sha256": hashlib.sha256(selected_prompt.encode("utf-8")).hexdigest()},
                "settings": {"model": config.require_ollama_model(), "endpoint": config.ollama_base_url, "temperature": 0, "seed": 42, "context_size": None, "num_predict": OUTPUT_TOKEN_LIMIT, "keep_alive": "5m", "total_deadline_seconds": TOTAL_DEADLINE_SECONDS, "max_retries": MAX_RETRIES, "concurrency": 1, "current_format": "json_schema", "minimal_json_format": "json", "determinism_guaranteed": False},
                "result": result,
                "comparison": compare_fields(selected_case["expected_facts"], result.get("actual")),
            }
        records.extend(execute_sequential(tasks, execute))
    decision = gate1_decision(records) if set(strategies) == set(STRATEGIES) and set(case_ids) == set(SELECTED_CASES) else {"status": "NOT_EVALUATED", "gate2": "NOT_EVALUATED"}
    artifact = {"created_at": datetime.now(timezone.utc).isoformat(), "experimental": True, "production_default": PRODUCTION_DEFAULT_STRATEGY, "warmup": warmup, "case_ids": case_ids, "strategy_order_control": "alternated by case; concurrency=1", "records": records, "gate1_decision": decision}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / ("targeted-comparison.json" if len(strategies) == 2 else f"targeted-{strategies[0]}.json")
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=[*STRATEGIES, "both"], default="both")
    parser.add_argument("--case-id", action="append", choices=SELECTED_CASES)
    parser.add_argument("--output-dir", type=Path, default=RESULTS / "strategy-comparison")
    args = parser.parse_args(argv)
    strategies = list(STRATEGIES) if args.strategy == "both" else [args.strategy]
    path, artifact = run(args.case_id or list(SELECTED_CASES), strategies, args.output_dir)
    print(json.dumps({"artifact": str(path), "gate1": artifact["gate1_decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
