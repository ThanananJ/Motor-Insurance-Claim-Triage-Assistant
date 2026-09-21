from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from src.monitoring.dashboard import LEGACY_REQUEST, _date, _request_identity, _thailand_timestamp, technical_dashboard
from src.monitoring.models import EventType, MonitoringEvent, MonitoringFilter
from src.monitoring.repository import MonitoringRepository
from src.monitoring.service import MonitoringService
from src.schemas import ClaimFacts, ClaimInput
from src.services.triage_service import TriageService


PROMPTS = ("focused-event-exclusion", "focused-history-risk", "focused-late-reason")


class CorrelatedExtractor:
    def __init__(self, monitoring: MonitoringService):
        self.monitoring = monitoring
        self.request_id = ""

    def set_monitoring_context(self, request_id: str) -> None:
        self.request_id = request_id

    def extract(self, claim):
        for prompt in PROMPTS:
            self.monitoring.record(
                EventType.LLM_PROMPT_PREPARED, self.request_id, prompt_name=prompt,
                prompt_token_count=100, max_prompt_tokens=32512,
                remaining_prompt_capacity_tokens=32412, context_usage_percent=0.31,
                context_status="HEALTHY", token_count_available=True,
            )
        return SimpleNamespace(success=True, facts=ClaimFacts(event_type="theft"), provider="fake", model="fake", failed_groups=[])


def _claim(marker: str) -> ClaimInput:
    return ClaimInput(claim_id=marker, claim_description=marker, documents_submitted=[])


def test_one_submit_has_one_request_id_and_three_prompt_rows(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    monitoring = MonitoringService(repository)
    TriageService(CorrelatedExtractor(monitoring), monitoring_service=monitoring).prepare_claim(_claim("PRIVATE-1"))
    rows = repository.query()
    request_ids = {row["request_id"] for row in rows}
    prepared = [row for row in rows if row["event_type"] == "LLM_PROMPT_PREPARED"]
    assert len(request_ids) == 1
    assert len(prepared) == 3
    assert {row["request_id"] for row in prepared} == request_ids
    assert {row["prompt_name"] for row in prepared} == set(PROMPTS)


def test_two_submits_have_two_request_ids_and_three_prompts_each(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    monitoring = MonitoringService(repository)
    service = TriageService(CorrelatedExtractor(monitoring), monitoring_service=monitoring)
    service.prepare_claim(_claim("PRIVATE-1"))
    service.prepare_claim(_claim("PRIVATE-2"))
    prepared = [row for row in repository.query() if row["event_type"] == "LLM_PROMPT_PREPARED"]
    ids = {row["request_id"] for row in prepared}
    assert len(ids) == 2
    assert all(sum(row["request_id"] == request_id for row in prepared) == 3 for request_id in ids)
    assert "PRIVATE-1" not in str(prepared) and "PRIVATE-2" not in str(prepared)


def test_dashboard_refresh_is_read_only_and_repository_survives_reopen(tmp_path):
    path = tmp_path / "monitoring.db"
    repository = MonitoringRepository(path)
    repository.insert(MonitoringEvent(request_id="12345678-full", event_type=EventType.REQUEST_STARTED))
    before = repository.query()
    technical_dashboard(repository)
    technical_dashboard(repository)
    assert repository.query() == before
    assert MonitoringRepository(path).query() == before


def test_thailand_display_and_filter_boundaries_across_midnight(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    repository.insert(MonitoringEvent(
        request_id="at-midnight", event_type=EventType.REQUEST_STARTED,
        timestamp_utc=datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc),
    ))
    repository.insert(MonitoringEvent(
        request_id="before-midnight", event_type=EventType.REQUEST_STARTED,
        timestamp_utc=datetime(2026, 9, 20, 16, 59, 59, tzinfo=timezone.utc),
    ))
    rows = repository.query(MonitoringFilter(start_utc=_date("2026-09-21"), end_utc=_date("2026-09-21", end=True)))
    assert [row["request_id"] for row in rows] == ["at-midnight"]
    assert _thailand_timestamp("2026-09-20T17:00:00+00:00") == "2026-09-21 00:00:00"


def test_dashboard_request_filter_short_full_id_and_legacy_label(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    repository.insert(MonitoringEvent(
        request_id="12345678-abcd", event_type=EventType.LLM_PROMPT_PREPARED,
        prompt_name=PROMPTS[0], prompt_token_count=100, max_prompt_tokens=32512,
        remaining_prompt_capacity_tokens=32412, context_usage_percent=0.31,
        context_status="HEALTHY", token_count_available=True,
    ))
    rows = technical_dashboard(repository, request_id="12345678")[2]
    assert rows[0][0:2] == ["12345678", "12345678-abcd"]
    assert technical_dashboard(repository, request_id="no-match")[2] == []
    assert _request_identity(None) == ("LEGACY", LEGACY_REQUEST)


def test_dashboard_rows_use_thailand_time_attempt_and_source(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    repository.insert(MonitoringEvent(
        request_id="abcdefgh-full", event_type=EventType.LLM_PROMPT_PREPARED,
        timestamp_utc=datetime(2026, 9, 21, 6, 18, 34, tzinfo=timezone.utc),
        prompt_name=PROMPTS[0], retry_count=1, is_synthetic=True,
        prompt_token_count=845, max_prompt_tokens=32512,
        remaining_prompt_capacity_tokens=31667, context_usage_percent=2.598,
        context_status="HEALTHY", token_count_available=True,
    ))
    row = technical_dashboard(repository)[2][0]
    assert row[:5] == ["abcdefgh", "abcdefgh-full", "2026-09-21 13:18:34", PROMPTS[0], 2]
    assert row[7] == "845 / 32,512"
    assert row[-1] == "Synthetic"


def test_latest_request_is_first_and_each_request_stays_grouped(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    for request_id, hour in (("older-request", 1), ("newer-request", 2)):
        for minute, prompt in enumerate(PROMPTS):
            repository.insert(MonitoringEvent(
                request_id=request_id, event_type=EventType.LLM_PROMPT_PREPARED,
                timestamp_utc=datetime(2026, 9, 21, hour, minute, tzinfo=timezone.utc),
                prompt_name=prompt, prompt_token_count=100, max_prompt_tokens=32512,
                remaining_prompt_capacity_tokens=32412, context_usage_percent=0.31,
                context_status="HEALTHY", token_count_available=True,
            ))
    rows = technical_dashboard(repository)[2]
    assert [row[1] for row in rows] == ["newer-request"] * 3 + ["older-request"] * 3
    assert [row[3] for row in rows[:3]] == list(PROMPTS)
