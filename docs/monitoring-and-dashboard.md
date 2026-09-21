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

Prompt preflight runs before every focused provider attempt:

```text
Assemble focused prompt
  → apply Qwen chat template
  → count tokens
  → calculate capacity/status
  → persist allow-listed numeric/category telemetry
  → call Ollama (unless OVER_LIMIT)
```

The tokenizer is `Qwen/Qwen2.5-3B-Instruct`, loaded lazily through Transformers and cached. The model capability is 131,072 total context tokens, but operational decisions use the effective application/Ollama runtime context. The current configured default is `OLLAMA_NUM_CTX=32768`, with 256 reserved output tokens, so `max_prompt_tokens=32512`; `context_source` is `application_num_ctx`.

Each Claim Form submit receives one random UUID `request_id`. The same full UUID is propagated through request, extraction, all three focused prompts, retry attempts, schema, fallback, confirmation, triage, and completion/failure events. `retry_count` distinguishes attempts without creating a new request. Thus three prompt rows sharing one Request ID represent one workflow, not three claim submissions. The Technical Dashboard shows an eight-character Request value for scanning plus the full copyable ID; missing legacy IDs render as `LEGACY/UNKNOWN` rather than a fabricated UUID. UTC events cover request
start/completion/failure, extraction start/completion/failure, schema
validation, fallback, human confirmation/override, deterministic triage, and
the current unavailable human-final-decision state. Monitoring is attached to
`TriageService`; it observes but does not change Policy or routing.

## Stored and prohibited data

Storage is limited to UUIDs, UTC timestamps, versions, status/error categories,
latency, validation/fallback/retry/token availability fields, category/count
business indicators, route and coverage result, and human confirmation/override
metadata. Prompt input counts come from the Qwen chat-template preflight;
provider output-token counts remain null unless the provider supplies them.

The schema rejects unknown fields. It never stores raw claim text, full prompts,
raw model output, names, contact details, identity/vehicle/policy/claim numbers,
addresses, secrets, environment dumps, or human free-text notes. Override
reasons are restricted to `AI_MISSED_FACT`, `AI_UNSUPPORTED_FACT`,
`AMBIGUOUS_INPUT`, `NEW_EVIDENCE`, `OFFICER_JUDGMENT`, `PROVIDER_FAILURE`, or
`OTHER_WITHOUT_FREE_TEXT`.

Token events store only prompt name/version, model/tokenizer identifiers, count source, token counts, model capability, effective context, reserved output, maximum prompt capacity, remaining capacity, usage percent, status, over-limit flag, provider status, and latency. They never store the prompt, Policy text, schema text, claim content, or raw response. Counts are available before provider timeout, unavailability, parsing, or validation failure.

## Technical dashboard

The overview shows requests, completion/failure, provider success/errors,
schema pass, fallback, average/P95 latency, and health. Tables show recent
category-only failures, error/validation/fallback distributions, and model /
prompt / policy versions. Filters cover Thailand (`UTC+7`) dates, environment, model, prompt,
status, error category, and synthetic/runtime source. Prompt-token cards show average/P95 per claim, maximum prompt observed, average/highest usage, warning/critical/over-limit counts, and unavailable rate. A per-prompt table displays short/full Request ID, Thailand timestamp, prompt, attempt, `Input Prompt Tokens / Max Prompt Tokens`, usage, remaining capacity, status, and data source. The compact trend carries the same correlation fields. Latest requests appear first, with their prompts/attempts kept together. Prompt name and Request ID/prefix are additional filters.

SQLite continues to store timezone-aware UTC timestamps. Dashboard presentation converts each timestamp with Python `ZoneInfo("Asia/Bangkok")` and displays `YYYY-MM-DD HH:MM:SS` without a misleading `Z`. Date inputs on both dashboards are labelled Thailand (`UTC+7`); naive dates/times are interpreted in Bangkok and converted to UTC before repository filtering. Daily buckets use the Thailand calendar date, including events around local midnight.

Prompt capacity status uses centralized configuration: below 70% is `HEALTHY`, 70–<85% is `WARNING`, 85–100% is `CRITICAL`, above 100% is `OVER_LIMIT`, and unavailable tokenizer/config is `UNKNOWN`. Percentages use maximum prompt tokens, not the 128K model capability.

An `OVER_LIMIT` prompt is never sent to Ollama and is never silently truncated. The focused group returns safe `UNKNOWN` facts for human entry/confirmation, preserving deterministic triage after the human trust boundary. Tokenizer or monitoring failure remains fail-open.

## Management dashboard

The overview shows claim volume, completed triage, route rates, human override,
AI fallback, and missing-document cases. Tables show route, coverage, override
reason, and completed/failed distributions. Filters cover Thailand (`UTC+7`) dates, scenario,
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
The seed also includes three per-prompt token rows for healthy, warning,
critical, over-limit, and tokenizer-unavailable scenarios.

Dashboard refresh performs read-only queries and creates no new events. SQLite persistence means existing monitoring history remains after an application restart. Use the full Request ID to correlate UI observations with database/log investigations without exposing claim content.

Monitoring failure is fail-open: it logs only an exception category and does
not stop extraction, human confirmation, or deterministic triage.

## Known limitations and production improvements

This local prototype has one SQLite database, process-local review/request
correlation, manual refresh, no authentication/RBAC, no distributed tracing,
no alerts, and no retention/backup policy. A production version should add
centralized encrypted storage, access controls, retention/deletion policy,
multi-process correlation, immutable audit governance, and separately governed
label-based accuracy reporting.

Tokenizer files must be downloaded/cached separately on a network-enabled
machine. If unavailable, the dashboard truthfully shows null/`UNKNOWN`; it does
not substitute word, character, GPT-tokenizer, or heuristic estimates.
