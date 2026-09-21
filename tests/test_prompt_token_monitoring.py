from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from src.config import AppConfig
from src.llm.base import LLMTimeoutError
from src.monitoring.dashboard import technical_dashboard
from src.monitoring.models import EventType, MonitoringEvent
from src.monitoring.prompt_tokens import PromptTokenCounter, PromptTokenResult, _load_tokenizer
from src.monitoring.repository import MonitoringRepository
from src.monitoring.service import MonitoringService
from src.services.focused_claim_extractor import FocusedClaimExtractor
from tests.p1_fakes import FixedPolicyRetriever


class FakeTokenizer:
    def __init__(self):
        self.messages = None

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        self.messages = messages
        assert tokenize is True and add_generation_prompt is True
        return list(range(len(messages[0]["content"])))


def test_counts_complete_assembled_prompt_through_chat_template():
    tokenizer = FakeTokenizer()
    counter = PromptTokenCounter(AppConfig(), tokenizer_loader=lambda: tokenizer)
    assembled = "SYSTEM + FOCUSED + POLICY + SCHEMA + CLAIM"
    result = counter.count(assembled)
    assert tokenizer.messages == [{"role": "user", "content": assembled}]
    assert result.prompt_token_count == len(assembled)
    assert result.max_prompt_tokens == 32512
    assert result.remaining_prompt_capacity_tokens == 32512 - len(assembled)


def test_capacity_boundaries_and_runtime_context_not_model_capability():
    def result_for(count):
        return PromptTokenCounter(
            AppConfig(ollama_num_ctx=1000, reserved_output_tokens=100),
            tokenizer_loader=lambda: SimpleNamespace(apply_chat_template=lambda *args, **kwargs: range(count)),
        ).count("assembled")

    assert result_for(629).context_status == "HEALTHY"
    assert result_for(630).context_status == "WARNING"
    assert result_for(765).context_status == "CRITICAL"
    over = result_for(901)
    assert over.context_status == "OVER_LIMIT"
    assert over.max_prompt_tokens == 900
    assert over.model_capability_context_tokens == 131072


def test_tokenizer_unavailable_is_explicit_and_fail_open():
    def unavailable():
        raise OSError("offline")

    result = PromptTokenCounter(AppConfig(), tokenizer_loader=unavailable).count("private prompt")
    assert result.token_count_available is False
    assert result.prompt_token_count is None
    assert result.context_status == "UNKNOWN"
    assert result.token_count_error_category == "TOKENIZER_UNAVAILABLE"


def test_runtime_tokenizer_loader_is_cached():
    assert hasattr(_load_tokenizer, "cache_info")
    assert _load_tokenizer.cache_info().maxsize == 1


class CountingProvider:
    provider_name = "fake"
    model_name = "qwen2.5:3b"

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def invoke_structured(self, prompt, schema):
        self.calls += 1
        if self.fail:
            raise LLMTimeoutError("timeout")
        values = {name: "unknown" for name in schema.model_fields}
        if "event_type" in values:
            values["event_type"] = "unknown"
        return values


class FixedCounter:
    def __init__(self, result):
        self.result = result
        self.prompts = []

    def count(self, prompt):
        self.prompts.append(prompt)
        return self.result


def token_result(count=100, *, over=False):
    return PromptTokenResult(
        token_count_available=True, prompt_token_count=count,
        remaining_prompt_capacity_tokens=32512 - count,
        context_usage_percent=count / 32512 * 100,
        context_status="OVER_LIMIT" if over else "HEALTHY",
        over_prompt_limit=over,
    )


def test_three_focused_prompts_counted_separately_before_provider(claim_factory, tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    provider = CountingProvider()
    counter = FixedCounter(token_result())
    extractor = FocusedClaimExtractor(provider, FixedPolicyRetriever(), token_counter=counter, monitoring_service=MonitoringService(repository))
    extractor.set_monitoring_context("request-1")
    extractor.extract(claim_factory(claim_description="CLAIM_MARKER"))
    prepared = [row for row in repository.query() if row["event_type"] == "LLM_PROMPT_PREPARED"]
    assert provider.calls == 3
    assert {row["prompt_name"] for row in prepared} == {"focused-event-exclusion", "focused-history-risk", "focused-late-reason"}
    assert all("CLAIM_MARKER" in prompt and "Policy" in prompt for prompt in counter.prompts)
    assert "CLAIM_MARKER" not in str(prepared)


def test_over_limit_never_calls_provider_and_returns_safe_unknown(claim_factory, tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    provider = CountingProvider()
    extractor = FocusedClaimExtractor(provider, FixedPolicyRetriever(), token_counter=FixedCounter(token_result(33000, over=True)), monitoring_service=MonitoringService(repository))
    extractor.set_monitoring_context("request-over")
    result = extractor.extract(claim_factory())
    assert provider.calls == 0
    assert result.success is False
    assert all(group.error_code == "prompt_context_over_limit" for group in result.groups)
    assert all(row["provider_status"] == "not_called" for row in repository.query() if row["event_type"] == "LLM_PROMPT_FAILED")


def test_provider_timeout_keeps_preflight_token_count(claim_factory, tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    provider = CountingProvider(fail=True)
    extractor = FocusedClaimExtractor(provider, FixedPolicyRetriever(), token_counter=FixedCounter(token_result(845)), monitoring_service=MonitoringService(repository))
    extractor.set_monitoring_context("request-timeout")
    extractor.extract(claim_factory())
    rows = repository.query()
    assert any(row["event_type"] == "LLM_PROMPT_PREPARED" and row["prompt_token_count"] == 845 for row in rows)
    assert any(row["event_type"] == "LLM_PROMPT_FAILED" and row["provider_error_category"] == "PROVIDER_TIMEOUT" for row in rows)


def test_safe_migration_preserves_existing_rows(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE monitoring_events (event_id TEXT PRIMARY KEY, request_id TEXT, timestamp_utc TEXT, event_type TEXT)")
        connection.execute("INSERT INTO monitoring_events VALUES ('old', 'r', '2026-01-01T00:00:00+00:00', 'REQUEST_STARTED')")
    repository = MonitoringRepository(path)
    repository.initialize()
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(monitoring_events)")}
        assert connection.execute("SELECT COUNT(*) FROM monitoring_events WHERE event_id='old'").fetchone()[0] == 1
    assert {"prompt_token_count", "max_prompt_tokens", "context_status"} <= columns


def test_dashboard_prompt_table_and_null_tokens(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    repository.insert(MonitoringEvent(request_id="r", event_type=EventType.REQUEST_STARTED))
    repository.insert(MonitoringEvent(request_id="r", event_type=EventType.LLM_PROMPT_PREPARED, prompt_name="focused-event-exclusion", token_count_available=True, prompt_token_count=845, max_prompt_tokens=32512, remaining_prompt_capacity_tokens=31667, context_usage_percent=2.598, context_status="HEALTHY"))
    repository.insert(MonitoringEvent(request_id="r", event_type=EventType.LLM_PROMPT_PREPARED, prompt_name="focused-history-risk", token_count_available=False, token_count_error_category="TOKENIZER_UNAVAILABLE", context_status="UNKNOWN"))
    outputs = technical_dashboard(repository)
    assert "Prompt Token Capacity" in outputs[1]
    assert outputs[2][0][1] == "845 / 32,512"
    assert outputs[2][1][1] == "Unavailable"
