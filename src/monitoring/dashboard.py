"""Read-only dashboard adapters for Gradio."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from .metrics import summarize
from .models import MonitoringFilter
from .repository import MonitoringRepository


THAILAND_TZ = ZoneInfo("Asia/Bangkok")
LEGACY_REQUEST = "LEGACY/UNKNOWN"


def _date(value: str | None, *, end: bool = False):
    """Interpret timezone-free dashboard filters as Thailand local time."""
    if not (value or "").strip():
        return None
    text = value.strip()
    parsed = datetime.fromisoformat(text)
    if len(text) == 10:
        parsed = datetime.combine(date.fromisoformat(text), time.max if end else time.min)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=THAILAND_TZ)
    return parsed.astimezone(timezone.utc)


def _thailand_timestamp(value: str | datetime | None) -> str:
    if not value:
        return "UNKNOWN"
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(THAILAND_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _request_identity(value: str | None) -> tuple[str, str]:
    full = (value or "").strip() or LEGACY_REQUEST
    return (full[:8] if full != LEGACY_REQUEST else "LEGACY", full)


def _prompt_order(events: list[dict]) -> list[dict]:
    """Newest request first; preserve timestamp/prompt attempt order inside it."""
    latest: dict[str, str] = {}
    for event in events:
        request = (event.get("request_id") or "").strip() or LEGACY_REQUEST
        latest[request] = max(latest.get(request, ""), event.get("timestamp_utc") or "")
    request_order = sorted(latest, key=lambda request: latest[request], reverse=True)
    grouped: list[dict] = []
    for request in request_order:
        rows = [
            event for event in events
            if ((event.get("request_id") or "").strip() or LEGACY_REQUEST) == request
        ]
        grouped.extend(sorted(rows, key=lambda event: (
            event.get("timestamp_utc") or "", event.get("prompt_name") or "", event.get("retry_count") or 0,
        )))
    return grouped


def _synthetic(value: str) -> bool | None:
    return {"Synthetic only": True, "Runtime only": False}.get(value)


def _rows(counter: dict) -> list[list]:
    return [[key, value] for key, value in sorted(counter.items())]


def _daily(events: list[dict], *, management: bool = False) -> list[list]:
    days: dict[str, dict] = {}
    for item in events:
        day = _thailand_timestamp(item.get("timestamp_utc"))[:10]
        bucket = days.setdefault(day, {"requests": 0, "success": 0, "failure": 0, "fallback": 0, "latencies": [], "override": 0, "missing": 0})
        kind = item["event_type"]
        bucket["requests"] += kind == "REQUEST_STARTED"
        bucket["success"] += kind == "AI_EXTRACTION_COMPLETED"
        bucket["failure"] += kind in {"AI_EXTRACTION_FAILED", "REQUEST_FAILED"}
        bucket["fallback"] += kind == "FALLBACK_TRIGGERED"
        bucket["override"] += kind == "HUMAN_OVERRIDE_RECORDED"
        bucket["missing"] += kind == "TRIAGE_COMPLETED" and (item["missing_document_count"] or 0) > 0
        if item["latency_ms"] is not None:
            bucket["latencies"].append(item["latency_ms"])
    if management:
        return [[day, row["requests"], row["override"], row["missing"], row["failure"]] for day, row in sorted(days.items())]
    return [[day, row["requests"], row["success"], row["failure"], row["fallback"], round(sum(row["latencies"]) / len(row["latencies"]), 2) if row["latencies"] else None] for day, row in sorted(days.items())]


def technical_dashboard(
    repository: MonitoringRepository, start="", end="", environment="All", model="All",
    prompt_version="All", prompt_name="All", status="All", error="All", data_source="All",
    request_id="",
):
    filters = MonitoringFilter(
        start_utc=_date(start), end_utc=_date(end, end=True), environment=environment,
        model_name=model, prompt_version=prompt_version, status=status,
        prompt_name=prompt_name, error_category=error, synthetic=_synthetic(data_source),
        request_id_prefix=request_id,
    )
    events = repository.query(filters)
    metrics = summarize(events)
    if not metrics["total_requests"]:
        cards = "### Health: NO_DATA\nNo monitoring requests match the selected filters. Dashboard time is Thailand (UTC+7); storage remains UTC."
    else:
        percent = lambda value: "N/A" if value is None else f"{value:.1%}"
        cards = (
            f"### Health: {metrics['health_status']}\n"
            f"Requests **{metrics['total_requests']}** · Completed **{metrics['completed_requests']}** · Failed **{metrics['failed_requests']}**  \n"
            f"Provider success **{percent(metrics['provider_success_rate'])}** · Errors **{metrics['provider_error_count']}** · "
            f"Schema pass **{percent(metrics['schema_validity_rate'])}** · Fallback **{percent(metrics['fallback_rate'])}**  \n"
            f"Average latency **{metrics['average_latency_ms'] or 0:.1f} ms** · P95 **{metrics['p95_latency_ms'] or 0:.1f} ms** · Thailand (UTC+7)"
        )
    token_percent = lambda value: "N/A" if value is None else f"{value:.2f}%"
    token_cards = (
        "### Prompt Token Capacity\n"
        f"Average/claim **{metrics['average_prompt_tokens_per_claim'] or 0:,.1f}** · "
        f"P95/claim **{metrics['p95_prompt_tokens_per_claim'] or 0:,.0f}** · "
        f"Maximum prompt **{metrics['maximum_prompt_tokens_observed'] or 0:,}**  \n"
        f"Average usage **{token_percent(metrics['average_context_usage_percent'])}** · "
        f"Highest usage **{token_percent(metrics['highest_context_usage_percent'])}** · "
        f"Warning/Critical/Over-limit **{metrics['context_status_distribution'].get('WARNING', 0)}/"
        f"{metrics['context_status_distribution'].get('CRITICAL', 0)}/"
        f"{metrics['context_status_distribution'].get('OVER_LIMIT', 0)}** · "
        f"Unavailable **{token_percent(None if metrics['token_count_unavailable_rate'] is None else metrics['token_count_unavailable_rate'] * 100)}**"
    )
    prepared = _prompt_order([event for event in events if event["event_type"] == "LLM_PROMPT_PREPARED"])
    prompt_rows = [
        [
            *_request_identity(event.get("request_id")),
            _thailand_timestamp(event.get("timestamp_utc")),
            event["prompt_name"],
            (event.get("retry_count") or 0) + 1,
            event.get("prompt_token_count"), event.get("max_prompt_tokens"),
            f"{event['prompt_token_count']:,} / {event['max_prompt_tokens']:,}" if event.get("prompt_token_count") is not None and event.get("max_prompt_tokens") else "Unavailable",
            round(event["context_usage_percent"], 2) if event.get("context_usage_percent") is not None else None,
            event.get("remaining_prompt_capacity_tokens"), event.get("context_status") or "UNKNOWN",
            "Synthetic" if event.get("is_synthetic") else "Runtime",
        ]
        for event in prepared
    ][:30]
    token_trend = [
        [*_request_identity(event.get("request_id")), _thailand_timestamp(event.get("timestamp_utc")),
         event["prompt_name"], event.get("prompt_token_count"), event.get("context_usage_percent"),
         (event.get("retry_count") or 0) + 1, "Synthetic" if event.get("is_synthetic") else "Runtime"]
        for event in prepared
    ][:100]
    recent_failed = [
        [_thailand_timestamp(event.get("timestamp_utc")), *_request_identity(event.get("request_id")), event["provider_error_category"] or event["validation_error_category"]]
        for event in events if event["event_type"] in {"AI_EXTRACTION_FAILED", "REQUEST_FAILED"}
    ][-20:][::-1]
    versions = Counter(
        (event["model_name"] or "not_available", event["prompt_version"], event["policy_version"])
        for event in events if event["event_type"] == "REQUEST_STARTED"
    )
    distributions = (
        [["Provider error", *row] for row in _rows(metrics["error_distribution"])]
        + [["Validation failure", *row] for row in _rows(metrics["validation_failure_distribution"])]
        + [["Fallback reason", *row] for row in _rows(metrics["fallback_reason_distribution"])]
    )
    return cards, token_cards, prompt_rows, token_trend, _daily(events), recent_failed, distributions, [[*key, value] for key, value in sorted(versions.items())]


def management_dashboard(
    repository: MonitoringRepository, start="", end="", scenario="All", route="All",
    coverage="All", data_source="All",
):
    events = repository.query(MonitoringFilter(
        start_utc=_date(start), end_utc=_date(end, end=True), scenario_category=scenario,
        route=route, coverage_status=coverage, synthetic=_synthetic(data_source),
    ))
    metrics = summarize(events)
    route_counts = metrics["route_distribution"]
    total_triage = sum(route_counts.values())
    rate = lambda name: (route_counts.get(name, 0) / total_triage) if total_triage else None
    percent = lambda value: "N/A" if value is None else f"{value:.1%}"
    cards = (
        f"### Operational overview ({'NO_DATA' if not metrics['total_requests'] else 'Thailand UTC+7'})\n"
        f"Claims **{metrics['total_requests']}** · Completed triage **{total_triage}** · "
        f"Manual review **{percent(rate('Manual review'))}** · Fraud review **{percent(rate('Fraud review'))}** · "
        f"Rejection review **{percent(rate('Rejection review'))}**  \n"
        f"Human override **{percent(metrics['human_override_rate'])}** · AI fallback **{percent(metrics['fallback_rate'])}** · "
        f"Missing-document cases **{percent(metrics['missing_document_case_rate'])}**"
    )
    distributions = (
        [["Route", *row] for row in _rows(route_counts)]
        + [["Coverage", *row] for row in _rows(metrics["coverage_distribution"])]
        + [["Override reason", *row] for row in _rows(metrics["override_reason_distribution"])]
    )
    workflow = [["Completed", metrics["completed_requests"]], ["Failed", metrics["failed_requests"]]]
    return cards, _daily(events, management=True), distributions, workflow
