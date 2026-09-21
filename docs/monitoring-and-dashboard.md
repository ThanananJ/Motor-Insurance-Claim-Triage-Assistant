# Runtime Monitoring and Dashboard

## Architecture and event flow

```text
Claim runtime workflow
  → fail-open MonitoringService
  → allow-listed MonitoringEvent validation
  → local SQLite repository
  → metrics and configurable health classification
  → read-only Technical / Management Gradio dashboards
```

Each session receives a random UUID `request_id`. UTC events cover request
start/completion/failure, extraction start/completion/failure, schema
validation, fallback, human confirmation/override, deterministic triage, and
the current unavailable human-final-decision state. Monitoring is attached to
`TriageService`; it observes but does not change Policy or routing.

## Stored and prohibited data

Storage is limited to UUIDs, UTC timestamps, versions, status/error categories,
latency, validation/fallback/retry/token availability fields, category/count
business indicators, route and coverage result, and human confirmation/override
metadata. Token counts remain null unless the provider actually supplies them.

The schema rejects unknown fields. It never stores raw claim text, full prompts,
raw model output, names, contact details, identity/vehicle/policy/claim numbers,
addresses, secrets, environment dumps, or human free-text notes. Override
reasons are restricted to `AI_MISSED_FACT`, `AI_UNSUPPORTED_FACT`,
`AMBIGUOUS_INPUT`, `NEW_EVIDENCE`, `OFFICER_JUDGMENT`, `PROVIDER_FAILURE`, or
`OTHER_WITHOUT_FREE_TEXT`.

## Technical dashboard

The overview shows requests, completion/failure, provider success/errors,
schema pass, fallback, average/P95 latency, and health. Tables show recent
category-only failures, error/validation/fallback distributions, and model /
prompt / policy versions. Filters cover UTC dates, environment, model, prompt,
status, error category, and synthetic/runtime source.

## Management dashboard

The overview shows claim volume, completed triage, route rates, human override,
AI fallback, and missing-document cases. Tables show route, coverage, override
reason, and completed/failed distributions. Filters cover UTC dates, scenario,
route, coverage, and synthetic/runtime source.

High override is not automatically poor model quality: new evidence and officer
judgment can legitimately change facts. These are operational indicators, not
final-claim accuracy. Accuracy requires a separate labelled ground-truth study.

## Health thresholds

Initial thresholds are centralized in `src/monitoring/health.py`:

| Metric | Healthy | Warning | Critical |
|---|---:|---:|---:|
| Provider success | ≥95% | 80–<95% | <80% |
| Schema validity | ≥95% | 80–<95% | <80% |
| Fallback | ≤5% | >5–20% | >20% |
| P95 latency | ≤10s | >10–30s | >30s |
| Workflow failure | ≤2% | >2–10% | >10% |

No requests produces `NO_DATA`, never `HEALTHY`. These thresholds are editable
prototype configuration, not fixed business standards.

## Synthetic data and operations

`uv run python -m monitoring.seed_demo_data` explicitly adds synthetic success,
timeout, schema failure, fallback, override, all review routes, and missing-
document examples. Synthetic rows are labelled and filterable. Nothing seeds on
app startup. The database is `data/runtime_monitoring.db` and is Git-ignored.

Monitoring failure is fail-open: it logs only an exception category and does
not stop extraction, human confirmation, or deterministic triage.

## Known limitations and production improvements

This local prototype has one SQLite database, process-local review/request
correlation, manual refresh, no authentication/RBAC, no distributed tracing,
no alerts, and no retention/backup policy. A production version should add
centralized encrypted storage, access controls, retention/deletion policy,
multi-process correlation, immutable audit governance, and separately governed
label-based accuracy reporting.
