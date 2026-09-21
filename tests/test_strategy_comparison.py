import time

import evaluation.strategy_comparison as strategy_comparison
from evaluation.strategy_comparison import (
    EXPERIMENTAL_STRATEGY,
    MAX_RETRIES,
    OUTPUT_TOKEN_LIMIT,
    PRODUCTION_DEFAULT_STRATEGY,
    _client,
    _run_process,
    compare_fields,
    execute_sequential,
    gate1_decision,
)
from src.config import AppConfig
from src.schemas import LateReasonExtraction


def _record(case_id, strategy, expected, actual, *, valid=True):
    return {
        "case_id": case_id,
        "strategy": strategy,
        "result": {"json_valid": valid, "pydantic_valid": valid, "actual": actual},
        "comparison": compare_fields(expected, actual),
    }


def test_compare_fields_flags_unsupported_critical_true():
    result = compare_fields({"illegal_racing": "unknown"}, {"illegal_racing": "true"})
    assert result["unsupported_critical_fields"] == ["illegal_racing"]


def test_gate1_requires_risk_improvement_and_all_safety_checks():
    cases = {
        "MODEL-RISK-001": {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"},
        "MODEL-LATE-001": {"late_submission_valid_reason": "true"},
        "MODEL-EVENT-001": {"event_type": "accidental_collision", "illegal_racing": "true"},
        "MODEL-EVENT-002": {"event_type": "unknown"},
    }
    records = []
    for case_id, expected in cases.items():
        current = {name: "unknown" for name in expected}
        minimal = dict(expected)
        records += [_record(case_id, "current", expected, current), _record(case_id, "minimal-json", expected, minimal)]
    decision = gate1_decision(records)
    assert decision["status"] == "PASS"
    assert decision["gate2"] == "RUN"


def test_gate1_rejects_control_hallucination():
    cases = {
        "MODEL-RISK-001": {"repeated_claims": "true", "severe_damage": "true", "weak_evidence": "true"},
        "MODEL-LATE-001": {"late_submission_valid_reason": "true"},
        "MODEL-EVENT-001": {"event_type": "accidental_collision", "illegal_racing": "true"},
        "MODEL-EVENT-002": {"event_type": "unknown"},
    }
    records = []
    for case_id, expected in cases.items():
        current = {name: "unknown" for name in expected}
        minimal = dict(expected)
        if case_id == "MODEL-EVENT-002":
            minimal["event_type"] = "other"
        records += [_record(case_id, "current", expected, current), _record(case_id, "minimal-json", expected, minimal)]
    assert gate1_decision(records)["status"] == "REJECTED_FOR_SAFETY"


def test_execution_controls_preserve_defaults_and_output_bound():
    client = _client(AppConfig(ollama_model="qwen2.5:3b"))
    assert client.num_predict == OUTPUT_TOKEN_LIMIT == 256
    assert MAX_RETRIES == 1
    assert PRODUCTION_DEFAULT_STRATEGY == "current"
    assert EXPERIMENTAL_STRATEGY == "minimal-json"


def test_tasks_execute_sequentially_in_declared_order():
    active = 0
    maximum = 0
    seen = []
    def executor(item):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        seen.append(item)
        active -= 1
        return item
    assert execute_sequential([1, 2, 3], executor) == [1, 2, 3]
    assert seen == [1, 2, 3]
    assert maximum == 1


def test_total_deadline_terminates_slow_process():
    started = time.perf_counter()
    completed = _run_process(time.sleep, (2,), 0.1)
    assert completed is False
    assert time.perf_counter() - started < 1.5


def test_timeout_is_bounded_retried_once_and_never_passes(monkeypatch):
    monkeypatch.setattr(strategy_comparison, "_run_process", lambda *args: False)
    result = strategy_comparison.invoke_bounded(
        "current",
        AppConfig(ollama_model="qwen2.5:3b"),
        "synthetic prompt",
        LateReasonExtraction,
        deadline_seconds=0.01,
        max_retries=1,
    )
    assert result["failure_category"] == "PROVIDER_TIMEOUT"
    assert result["success"] is False
    assert result["attempt_count"] == 2
    assert result["retry_count"] == 1
    assert result["fallback_triggered"] is True
