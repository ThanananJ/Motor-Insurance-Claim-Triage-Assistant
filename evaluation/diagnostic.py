"""Development-only live output pipeline diagnostic for synthetic cases.

This module is deliberately separate from production logging. It captures raw
model output only for committed synthetic evaluation cases and never stores the
full prompt or Policy text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from evaluation import PROMPT_VERSION
from evaluation.io import RESULTS, load_dataset
from evaluation.evaluators.model_evaluator import SPECS, _context
from src.config import AppConfig
from src.policy.loader import PolicyLoader
from src.schemas import ClaimInput
from src.services.focused_claim_extractor import build_focused_prompt


SELECTED_CASES = (
    "MODEL-EVENT-002",  # simple all-unknown control; passed live baseline
    "MODEL-RISK-001",   # explicit repeated claims + severe/weak evidence
    "MODEL-LATE-001",   # explicit valid late reason
    "MODEL-EVENT-001",  # explicit racing exclusion and collision event
)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)


def _message_snapshot(message: Any) -> dict[str, Any]:
    if message is None:
        return {}
    return {
        "type": type(message).__name__,
        "content": _jsonable(getattr(message, "content", None)),
        "tool_calls": _jsonable(getattr(message, "tool_calls", None)),
        "additional_kwargs": _jsonable(getattr(message, "additional_kwargs", None)),
        "response_metadata": _jsonable(getattr(message, "response_metadata", None)),
        "usage_metadata": _jsonable(getattr(message, "usage_metadata", None)),
    }


def _application_path(config: AppConfig, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
    timeline: dict[str, float] = {"request_started": time.perf_counter()}
    try:
        chat = ChatOllama(
            model=config.require_ollama_model(),
            base_url=config.ollama_base_url,
            temperature=0,
            validate_model_on_init=False,
            client_kwargs={"timeout": config.ollama_timeout_seconds},
        )
        runnable = chat.with_structured_output(schema, method="json_schema", include_raw=True)
        timeline["provider_call_started"] = time.perf_counter()
        envelope = runnable.invoke(prompt)
        timeline["provider_response_received"] = time.perf_counter()
        raw = envelope.get("raw") if isinstance(envelope, dict) else None
        parsed = envelope.get("parsed") if isinstance(envelope, dict) else None
        parsing_error = envelope.get("parsing_error") if isinstance(envelope, dict) else "unexpected envelope"
        timeline["parse_finished"] = time.perf_counter()
        validated = None
        validation_error = None
        try:
            validated = schema.model_validate(parsed).model_dump(mode="json")
        except (ValidationError, TypeError, ValueError) as exc:
            validation_error = f"{type(exc).__name__}: {exc}"
        timeline["validation_finished"] = time.perf_counter()
        return {
            "success": validated is not None and parsing_error is None,
            "envelope_type": type(envelope).__name__,
            "envelope_keys": sorted(envelope) if isinstance(envelope, dict) else [],
            "raw_message": _message_snapshot(raw),
            "langchain_parsed": _jsonable(parsed),
            "parsing_error": _jsonable(parsing_error),
            "pydantic_validated": validated,
            "normalized_output": validated,
            "evaluator_actual": validated,
            "fallback_triggered": validated is None,
            "error": validation_error,
            "timeline_ms": _timeline(timeline),
        }
    except Exception as exc:
        timeline["request_finished"] = time.perf_counter()
        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "fallback_triggered": True,
            "timeline_ms": _timeline(timeline),
        }


def _direct_path(config: AppConfig, prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
    started = time.perf_counter()
    payload = {
        "model": config.require_ollama_model(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": schema.model_json_schema(),
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        config.ollama_base_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.ollama_timeout_seconds) as response:
            response_received = time.perf_counter()
            envelope = json.loads(response.read().decode("utf-8"))
        content = envelope.get("message", {}).get("content")
        parsed = None
        parse_error = validation_error = None
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, TypeError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
        validated = None
        if parse_error is None:
            try:
                validated = schema.model_validate(parsed).model_dump(mode="json")
            except (ValidationError, TypeError, ValueError) as exc:
                validation_error = f"{type(exc).__name__}: {exc}"
        finished = time.perf_counter()
        metadata = {key: envelope.get(key) for key in ("model", "created_at", "done", "done_reason", "total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration")}
        return {
            "success": validated is not None,
            "response_envelope_keys": sorted(envelope),
            "raw_model_content": content,
            "response_metadata": metadata,
            "json_dictionary": parsed,
            "pydantic_validated": validated,
            "parse_error": parse_error,
            "validation_error": validation_error,
            "latency_ms": {"provider": round((response_received - started) * 1000, 3), "parse_validation": round((finished - response_received) * 1000, 3), "total": round((finished - started) * 1000, 3)},
        }
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}", "latency_ms": {"total": round((time.perf_counter() - started) * 1000, 3)}}


def _timeline(points: dict[str, float]) -> dict[str, float]:
    first = points["request_started"]
    return {name: round((value - first) * 1000, 3) for name, value in points.items()}


def run(case_ids: list[str], runs: int, output_dir: Path) -> Path:
    if runs not in (1, 2):
        raise ValueError("Diagnostic runs must be 1 or 2")
    cases = {item["case_id"]: item for item in load_dataset("model").cases}
    unknown = sorted(set(case_ids) - set(cases))
    if unknown:
        raise ValueError("Unknown case ID(s): " + ", ".join(unknown))
    config = AppConfig.from_env()
    policy = PolicyLoader().load_exact()
    records = []
    for case_id in case_ids:
        case = cases[case_id]
        prompt_name = case["prompt_name"]
        prompt_path, schema = SPECS[prompt_name]
        claim = ClaimInput.model_validate(case["claim_input"])
        prompt = build_focused_prompt(prompt_path=prompt_path, policy_context=policy, claim_context=_context(prompt_name, claim), schema=schema)
        prompt_meta = {"name": prompt_name, "version": PROMPT_VERSION, "length": len(prompt), "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}
        for run_number in range(1, runs + 1):
            application = _application_path(config, prompt, schema)
            direct = _direct_path(config, prompt, schema)
            records.append({
                "case_id": case_id,
                "run": run_number,
                "synthetic_case": True,
                "model": config.require_ollama_model(),
                "endpoint": config.ollama_base_url,
                "prompt": prompt_meta,
                "expected": case["expected_facts"],
                "application_path": application,
                "direct_path": direct,
                "paths_use_same_prompt_hash": True,
                "comparison_note": "Both paths use the same prompt, schema, model, and temperature. LangChain transport/adaptation is not guaranteed byte-identical to the direct Ollama request.",
            })
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"diagnostic-{stamp}.json"
    artifact = {"diagnostic_only": True, "created_at": datetime.now(timezone.utc).isoformat(), "selected_case_ids": case_ids, "runs_per_case": runs, "records": records}
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trace live synthetic outputs without production logging")
    parser.add_argument("--case-id", action="append", choices=SELECTED_CASES, help="Repeat for selected cases; defaults to all four representatives")
    parser.add_argument("--runs", type=int, choices=[1, 2], default=1)
    parser.add_argument("--output-dir", type=Path, default=RESULTS / "diagnostic")
    args = parser.parse_args(argv)
    path = run(args.case_id or list(SELECTED_CASES), args.runs, args.output_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
