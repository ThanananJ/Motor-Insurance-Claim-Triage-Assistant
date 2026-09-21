from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.monitoring.dashboard import management_dashboard, technical_dashboard
from src.monitoring.health import HealthThresholds, classify_health
from src.monitoring.metrics import summarize
from src.monitoring.models import EventType, MonitoringEvent, MonitoringFilter
from src.monitoring.repository import MonitoringRepository
from src.monitoring.service import MonitoringService
from src.schemas import ClaimFacts, ClaimInput, ConfirmedClaimFacts
from src.services.triage_service import TriageService


def event(request_id="r1", event_type=EventType.REQUEST_STARTED, **fields):
    return MonitoringEvent(request_id=request_id, event_type=event_type, **fields)


def test_database_initialization_insert_duplicate_and_filters(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    repository.initialize()
    item = event(status="started", is_synthetic=True)
    assert repository.insert(item) is True
    assert repository.insert(item) is False
    assert len(repository.query(MonitoringFilter(status="started", synthetic=True))) == 1
    assert repository.query(MonitoringFilter(synthetic=False)) == []
    assert repository.query(MonitoringFilter(start_utc=datetime.now(timezone.utc) + timedelta(days=1))) == []


@pytest.mark.parametrize("forbidden", ["raw_claim_text", "full_prompt", "raw_model_response", "customer_name", "officer_note"])
def test_privacy_model_rejects_prohibited_fields(forbidden):
    with pytest.raises(ValidationError):
        MonitoringEvent(request_id="r1", event_type=EventType.REQUEST_STARTED, **{forbidden: "PII"})


def test_free_text_override_reason_is_rejected():
    with pytest.raises(ValidationError):
        event(override_reason_category="customer said something private")


def test_metrics_rates_distributions_and_p95():
    events = [
        event(event_type=EventType.REQUEST_STARTED).model_dump(mode="json"),
        event(event_type=EventType.AI_EXTRACTION_COMPLETED, provider_status="success", latency_ms=100).model_dump(mode="json"),
        event(event_type=EventType.SCHEMA_VALIDATION_COMPLETED, schema_valid=True).model_dump(mode="json"),
        event(event_type=EventType.HUMAN_OVERRIDE_RECORDED, human_override=True, override_field_count=1, override_reason_category="NEW_EVIDENCE").model_dump(mode="json"),
        event(event_type=EventType.TRIAGE_COMPLETED, route="Manual review", coverage_status="Possibly covered", missing_document_count=1, risk_signal_count=1, latency_ms=200).model_dump(mode="json"),
        event(event_type=EventType.REQUEST_COMPLETED).model_dump(mode="json"),
    ]
    metrics = summarize(events)
    assert metrics["provider_success_rate"] == 1
    assert metrics["schema_validity_rate"] == 1
    assert metrics["fallback_rate"] == 0
    assert metrics["human_override_rate"] == 1
    assert metrics["route_distribution"] == {"Manual review": 1}
    assert metrics["p95_latency_ms"] == 200


def test_empty_metrics_and_health_thresholds():
    assert summarize([])["health_status"] == "NO_DATA"
    base = {"total_requests": 1, "provider_success_rate": .99, "schema_validity_rate": .99, "fallback_rate": 0, "p95_latency_ms": 1, "workflow_failure_rate": 0}
    assert classify_health(base) == "HEALTHY"
    assert classify_health({**base, "fallback_rate": .1}) == "WARNING"
    assert classify_health({**base, "fallback_rate": .3}) == "CRITICAL"
    assert classify_health({**base, "provider_success_rate": .9}, HealthThresholds(provider_warning=.85)) == "HEALTHY"


class BrokenRepository:
    def insert(self, event):
        raise OSError("disk unavailable")


class Extractor:
    def __init__(self, fail=False):
        self.fail = fail

    def extract(self, claim):
        if self.fail:
            raise TimeoutError("private provider detail")
        return SimpleNamespace(success=True, facts=ClaimFacts(event_type="theft"), provider="fake", model="fake", failed_groups=[])


def claim():
    return ClaimInput(claim_id="PRIVATE-ID", claim_description="private raw text", documents_submitted=[])


def test_monitoring_write_failure_does_not_stop_triage():
    service = TriageService(Extractor(), monitoring_service=MonitoringService(BrokenRepository()))
    review = service.prepare_claim(claim())
    result = service.confirm_and_analyze(review, ConfirmedClaimFacts(claim_id="PRIVATE-ID", facts=ClaimFacts(event_type="theft"), confirmed_by_human=True))
    assert result.recommended_routing.value == "Manual review"


def test_runtime_success_override_and_triage_events_without_pii(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    service = TriageService(Extractor(), monitoring_service=MonitoringService(repository))
    review = service.prepare_claim(claim())
    service.confirm_and_analyze(review, ConfirmedClaimFacts(claim_id="PRIVATE-ID", facts=ClaimFacts(event_type="flood"), confirmed_by_human=True, officer_note="private note"))
    events = repository.query()
    types = {row["event_type"] for row in events}
    assert {"REQUEST_STARTED", "AI_EXTRACTION_COMPLETED", "SCHEMA_VALIDATION_COMPLETED", "HUMAN_CONFIRMATION_COMPLETED", "HUMAN_OVERRIDE_RECORDED", "TRIAGE_COMPLETED", "REQUEST_COMPLETED"} <= types
    serialized = str(events)
    assert "private raw text" not in serialized
    assert "PRIVATE-ID" not in serialized
    assert "private note" not in serialized


def test_provider_timeout_records_failure_and_fallback(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    review = TriageService(Extractor(fail=True), monitoring_service=MonitoringService(repository)).prepare_claim(claim())
    events = repository.query()
    assert review.proposal.source == "safe_fallback"
    assert any(row["provider_error_category"] == "PROVIDER_TIMEOUT" for row in events)
    assert any(row["event_type"] == "FALLBACK_TRIGGERED" for row in events)


def test_dashboard_empty_state_and_synthetic_separation(tmp_path):
    repository = MonitoringRepository(tmp_path / "monitoring.db")
    assert "NO_DATA" in technical_dashboard(repository)[0]
    assert "NO_DATA" in management_dashboard(repository)[0]
    repository.insert(event(is_synthetic=True))
    assert summarize(repository.query(MonitoringFilter(synthetic=False)))["total_requests"] == 0
    assert summarize(repository.query(MonitoringFilter(synthetic=True)))["total_requests"] == 1
