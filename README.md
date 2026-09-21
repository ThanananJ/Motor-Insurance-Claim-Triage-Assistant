# Motor Insurance Claim Triage Assistant

Local hybrid-AI prototype that helps Claim Officers perform initial motor-insurance claim triage. The AI extracts and proposes structured claim facts, Pydantic validates the structure, and a human must review, correct, and explicitly confirm those facts before deterministic coverage, document, risk, and routing rules run. The output is a recommendation only: AI never makes the final claim decision.

The repository also provides three evaluation levels, privacy-safe runtime monitoring, and read-only Technical and Management dashboards.

## Architecture

```text
Gradio Claim Form
→ Focused Prompt Extraction
→ Ollama / Qwen2.5:3b
→ Pydantic Validation
→ Proposed Claim Facts
→ Human Confirmation/Correction
→ Deterministic Triage Rules
→ Recommendation
→ Human Final Decision Boundary
→ Runtime Monitoring
→ SQLite
→ Technical/Management Dashboard
```

The three focused prompts cover event/exclusion, claim-history/risk, and late-submission reason facts. The complete, fixed Policy text is injected into every prompt as static full-policy grounding. This is not embeddings, vector search, or RAG. Strategy A (schema-constrained structured output) remains the production default.

## Prerequisites

- Python 3.11 or newer (the project declares `>=3.11`)
- [`uv`](https://docs.astral.sh/uv/)
- Ollama
- The local model `qwen2.5:3b`
- Windows PowerShell for the commands below

Verify the tools and installed models:

```powershell
python --version
uv --version
ollama --version
ollama list
```

Local-model latency and timeout behavior depend on CPU, GPU, RAM, and current system load. A GPU is helpful but not required by the repository.

## Clone and Setup

```powershell
git clone https://github.com/ThanananJ/Motor-Insurance-Claim-Triage-Assistant.git
cd Motor-Insurance-Claim-Triage-Assistant
Copy-Item .env.example .env
uv sync
```

`.env` is local configuration and is ignored by Git. The supported settings are:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_MODEL=qwen2.5:3b
```

Do not put secrets in committed files. The same values can be set for the current PowerShell session:

```powershell
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_TIMEOUT_SECONDS="60"
$env:OLLAMA_MODEL="qwen2.5:3b"
```

## Ollama Setup

```powershell
ollama pull qwen2.5:3b
ollama list
```

`ollama list` should show `qwen2.5:3b`. Many Windows installations already run Ollama as a background service. If requests cannot connect and no service is running, start it in a separate terminal:

```powershell
ollama serve
```

## Run the Application

```powershell
uv run python app.py
```

Open the URL printed by Gradio, normally `http://127.0.0.1:7860`. The local UI contains:

- **Claim Triage** — claim input and AI-proposed facts, followed by mandatory human confirmation/correction and the deterministic triage result.
- **Technical Dashboard** — provider, schema, fallback, latency, version, error, and health indicators.
- **Management Dashboard** — operational claim volume, route, coverage, override, fallback, and missing-document indicators.

Do not expose this local prototype on a public network.

## Testing and Evaluation

Use `--help` to inspect supported options:

```powershell
uv run python -m evaluation.runner --help
uv run python -m evaluation.strategy_comparison --help
```

### Full Regression Tests

```powershell
uv run pytest -q
```

The latest verified count is recorded in the final project handoff rather than hard-coded here. Normal pytest runs use fixtures/mocks and do not require Ollama.

### All Offline Evaluation Levels

```powershell
uv run python -m evaluation.runner --level all --mode fixture
```

This runs Model Fixture Evaluation, Component Evaluation, and service-level E2E Evaluation. Fixture results verify the evaluation framework and deterministic behavior; they do not establish real `qwen2.5:3b` accuracy. In particular, fixture F1 of 1.0 must not be presented as model accuracy.

### Model Evaluation

```powershell
uv run python -m evaluation.runner --level model --mode fixture
uv run python -m evaluation.runner --level model --mode live --runs 3
```

Fixture mode is offline. Live mode requires Ollama and may be slow or time out. `PROVIDER_TIMEOUT` and `PROVIDER_UNAVAILABLE` are not passes. The recorded Phase 2 live baseline is below the quality gates; see `results/evaluation/live-comparison.md`.

### Component Evaluation

```powershell
uv run python -m evaluation.runner --level component --mode fixture
```

This checks prompt construction, strict schemas/Pydantic validation, focused-output merge, deterministic rules and routing, safe fallback, and the human confirmation boundary.

### E2E Evaluation

```powershell
uv run python -m evaluation.runner --level e2e --mode fixture
uv run python -m evaluation.runner --level e2e --mode live --runs 1
```

E2E is service-level and does not automate browser clicks. Post-confirmation routing consumes human-confirmed facts, never unconfirmed AI proposals. Read extraction quality separately from deterministic routing correctness. Live E2E has the same Ollama latency and timeout caveats as live model evaluation.

### Strategy Comparison

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
uv run python -m evaluation.strategy_comparison --strategy both
```

Strategy A (`current`) is the production default. Strategy B (`minimal-json`) is experimental. The recorded final Gate 1 result is `INCONCLUSIVE` because provider timeouts left no complete comparison responses; Gate 2 must not run without complete Gate 1 responses. Execution is sequential (`concurrency=1`) with `num_predict=256`, a 30-second total deadline per attempt, and at most one retry for transient timeout/connection/provider failures.

### Reading Results

- `PASS` — applicable gates passed.
- `PARTIAL` — some evidence passed but the result is incomplete.
- `FAIL` — an applicable gate failed.
- `SKIPPED` — the evaluation did not run or was not applicable.
- `PROVIDER_UNAVAILABLE` — the configured provider/model could not be used.
- `PROVIDER_TIMEOUT` — the bounded provider call exceeded its deadline.
- `INCONCLUSIVE` — evidence was insufficient for a comparison decision.

Key metrics include accuracy, precision, recall, F1, schema validity, critical-risk recall, critical-exclusion recall, safe-fallback rate, and human-boundary compliance. Always read percentages from small datasets together with their numerator and denominator. Reports are written under `results/evaluation/`; see [`evaluation/README.md`](evaluation/README.md) for gates, datasets, and privacy details.

## Runtime Monitoring

```text
Runtime Workflow
→ Fail-open Monitoring Service
→ Allow-listed Event Validation
→ SQLite
→ Metrics and Health
→ Read-only Dashboards
```

Monitoring observes the workflow but never changes Policy, deterministic routing, or claim decisions. If monitoring initialization or an event write fails, the claim workflow continues (fail-open).

### Monitoring Database and Privacy

The application automatically creates `data/runtime_monitoring.db` when monitoring first initializes. Git ignores `*.db` and SQLite journal/WAL/SHM files; never commit them.

Monitoring stores only allow-listed categories, counts, status, UUID correlation, UTC timestamps, versions, route/coverage outputs, and latency/validation/fallback metadata. It does not store raw claims, full prompts, raw model responses, names, contact details, vehicle/policy/claim identifiers, secrets, PII, or human free-text notes.

### Seed and Clear Synthetic Demo Data

Seed labelled synthetic events explicitly (the app never seeds on startup):

```powershell
uv run python -m monitoring.seed_demo_data
```

Every seeded row has `is_synthetic=true`. Dashboards can filter **Synthetic only** or **Runtime only**. To delete synthetic rows while preserving runtime rows:

```powershell
uv run python -m monitoring.seed_demo_data --clear-synthetic --yes
```

Do not delete the database file or use broad SQL deletion as the normal cleanup method.

### Technical Dashboard

1. Run `uv run python app.py` and open the Gradio URL.
2. Open **Technical Dashboard**.
3. Choose Synthetic, Runtime, or All data; set UTC date, environment, model, prompt, status, and error filters.
4. Select **Refresh Technical Dashboard**.

It shows total requests, completed/failed workflow, provider success/errors, schema pass rate, fallback rate, average/P95 latency, error/fallback distributions, version breakdown, and health.

Health is `HEALTHY`, `WARNING`, `CRITICAL`, or `NO_DATA`. Initial operational thresholds are:

| Metric | Healthy | Warning | Critical |
|---|---:|---:|---:|
| Provider success | ≥95% | 80–<95% | <80% |
| Schema validity | ≥95% | 80–<95% | <80% |
| Fallback | ≤5% | >5–20% | >20% |
| P95 latency | ≤10s | >10–30s | >30s |
| Workflow failure | ≤2% | >2–10% | >10% |

No matching requests produces `NO_DATA`. These are configurable initial operational thresholds, not permanent business standards.

### Management Dashboard

Open **Management Dashboard**, select the UTC date range, scenario, route, coverage, and Synthetic/Runtime source, then select **Refresh Management Dashboard**. It shows claim volume, completed triage, Manual Review, Fraud Review, Rejection Review, human override, AI fallback, missing-document cases, and route/coverage distributions.

A high override rate does not necessarily mean poor model quality: new evidence or Claim Officer judgment may justify a correction. The dashboard is an operational indicator and cannot report final claim accuracy without labelled ground truth.

### Generate One Runtime Monitoring Record

1. Clear synthetic data or select **Runtime only**.
2. Open **Claim Triage** and enter a synthetic claim only.
3. Run AI extraction, or let safe fallback populate reviewable facts.
4. Review, correct, and explicitly confirm the facts.
5. Run deterministic triage.
6. Open each dashboard, select **Runtime only**, and refresh.
7. Verify request, fallback, override, and route indicators as applicable.

Never use real customer data or PII for a demo.

## Known Limitations

- Local SQLite storage and process-local request correlation only.
- Manual dashboard refresh; no alerting.
- No authentication or RBAC; do not expose the app publicly.
- No retention/backup policy or distributed tracing.
- Live Ollama latency and timeout behavior varies by hardware and load.
- Strategy comparison remains inconclusive, and current live model quality is below the live quality gates.
- Runtime scenario category is not inferred from claim text solely for monitoring.
- Human final decision remains `not_available` because the UI does not capture it.
- This is a local prototype, not a production-ready deployment.

## Project Structure

```text
app.py                  Gradio claim workflow and dashboards
data/                   fixed Policy and synthetic assignment cases
evaluation/             model, component, E2E, and strategy evaluation
monitoring/             explicit synthetic monitoring-data CLI
src/monitoring/         contracts, fail-open service, SQLite, metrics, dashboards
src/rules/              deterministic coverage/document/risk/routing rules
src/services/           focused extraction, confirmation, and triage workflow
tests/                  regression, evaluation, monitoring, and safety tests
results/evaluation/     small redacted evaluation evidence and summaries
```

## Additional Documentation

- [`evaluation/README.md`](evaluation/README.md)
- [`docs/monitoring-and-dashboard.md`](docs/monitoring-and-dashboard.md)
- [`docs/solution-design.md`](docs/solution-design.md)
- [`docs/limitations-and-roadmap.md`](docs/limitations-and-roadmap.md)

The Human Claim Officer remains responsible for the final claim decision.
