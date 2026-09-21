import pytest

from evaluation.diagnostic import SELECTED_CASES, _message_snapshot, _timeline


def test_diagnostic_scope_is_limited_to_four_existing_cases():
    assert len(SELECTED_CASES) == 4
    assert len(set(SELECTED_CASES)) == 4


def test_diagnostic_snapshot_keeps_response_data_but_not_prompt_or_environment():
    class Message:
        content = '{"late_submission_valid_reason":"true"}'
        tool_calls = []
        additional_kwargs = {}
        response_metadata = {"done_reason": "stop"}
        usage_metadata = None

    snapshot = _message_snapshot(Message())
    assert snapshot["content"].startswith("{")
    assert "prompt" not in snapshot
    assert "environment" not in snapshot


def test_diagnostic_timeline_is_relative_milliseconds():
    assert _timeline({"request_started": 10.0, "provider_call_started": 10.25}) == {
        "request_started": 0.0,
        "provider_call_started": 250.0,
    }
