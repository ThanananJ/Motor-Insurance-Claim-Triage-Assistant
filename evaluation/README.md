# Evaluation Foundation — Phase 1 and Phase 2

This package evaluates three independent boundaries without automating the Gradio UI:

1. **Model** — each production focused prompt and strict Pydantic output schema; deterministic Policy/routing is excluded from this score.
2. **Component** — prompt construction, schema rejection, merge contracts, deterministic rules, safe fallback, explanation, and mandatory confirmation.
3. **E2E** — fixture extraction through human confirmation into deterministic coverage, documents, risk, routing, and recommendation output.

All committed cases are synthetic. JSONL audit records contain case IDs and structured expected/actual values, never customer names, registration numbers, policy numbers, full prompts, or raw production claim text.

## Commands

```bash
uv run python -m evaluation.runner --level model --mode fixture
uv run python -m evaluation.runner --level model --mode live --runs 3
uv run python -m evaluation.runner --level e2e --mode live --runs 1
uv run python -m evaluation.runner --level component
uv run python -m evaluation.runner --level e2e
uv run python -m evaluation.runner --level all --mode fixture
```

`fixture` (alias `offline`) needs no Ollama. `live` uses `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_TIMEOUT_SECONDS`. Provider/model failure is reported as `PROVIDER_UNAVAILABLE`; it is never converted to a passing model case. Token counts remain `null` with `token_usage_unavailable: true` because the current provider contract does not expose reliable usage metadata.

Reports are written to `results/evaluation/`: `latest-<level>.json`, per-run JSON, a redacted JSONL audit log, and `latest-summary.md`. The default `latest-*.json`, `latest-summary.md`, and `runs/` outputs are local generated artifacts and are Git-ignored because every evaluation run replaces or appends to them. Named evidence directories such as `phase3-final/`, `final-verification/`, and `strategy-comparison/` are curated, redacted snapshots and remain tracked deliberately.

Statuses: `PASS` meets the expected result; `PARTIAL` is reserved for an explicitly incomplete outcome; `FAIL` differs from ground truth; `SKIPPED` means no live case could be assessed; `PROVIDER_UNAVAILABLE` identifies the affected live case.

Quality gates are embedded with numerator/denominator metrics in every JSON report. Compare runs using `dataset_version`, `prompt_version`, `policy_version`, provider/model, timestamp, and run ID. The committed dataset is intentionally small, so percentages must be read with their counts.

The prototype uses complete static Policy injection through `ExactPolicyRetriever`; there is no vector or ranked retriever. Therefore `Retrieval Evaluation: Not Applicable in Current Implementation`. Recall@K and Precision@K are not reported.

The AI output remains advisory. The evaluator never uses an LLM route as ground truth and never bypasses `ConfirmedClaimFacts(confirmed_by_human=True)`.

## Windows live evaluation

Start the Ollama desktop application, then verify the exact target:

```powershell
ollama --version
ollama list
ollama show qwen2.5:3b
Invoke-RestMethod http://localhost:11434/api/version
```

Set configuration for the current PowerShell session when `.env` is not loaded
by the CLI process:

```powershell
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="qwen2.5:3b"
$env:OLLAMA_TIMEOUT_SECONDS="60"
uv run python -m evaluation.runner --level model --mode live --runs 3 --output-dir results/evaluation/live-baseline
```

Fixture evaluation validates the evaluator deterministically; it does not
measure Qwen. Live evaluation invokes Ollama and may vary or time out. Read every
percentage with its numerator/denominator. `PASS` satisfies all applicable
gates, `PARTIAL` has useful but incomplete results, `FAIL` violates a gate,
`SKIPPED` means no live invocation was assessable, and
`PROVIDER_UNAVAILABLE` applies to an affected invocation.

Live E2E compares the AI proposal with expected facts, then separately applies
synthetic human-confirmed ground truth to deterministic routing. This preserves
the real human boundary and prevents a poor proposal from being silently
treated as confirmed.

Phase 2 evidence is under `results/evaluation/live-baseline/`,
`results/evaluation/live-after-tuning/`, `results/evaluation/live-e2e/`, and
`results/evaluation/live-comparison.md`. The v2 tuning candidate was rejected;
the active production prompt version remains `focused-prompts-v1`.

## Development-only pipeline diagnostic

Use only with the committed synthetic cases. Diagnostic mode is disabled from
normal application and evaluation runs and never stores the full prompt:

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
uv run python -m evaluation.diagnostic --runs 1
uv run python -m evaluation.diagnostic --case-id MODEL-RISK-001 --runs 1
```

The command permits only four representative case IDs and at most two runs per
case. It writes raw synthetic evidence to `results/evaluation/diagnostic/` and
compares the current LangChain application path with a direct Ollama `/api/chat`
path using the same prompt hash and schema. It is not production logging.

## Experimental structured-output comparison

Strategy `current` is the production default. Strategy `minimal-json` is an
evaluation-only experiment and does not alter the application provider:

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
uv run python -m evaluation.strategy_comparison --strategy both
```

This tested command warms the model, alternates strategy order across the four
bounded diagnostic cases, and writes evidence to
`results/evaluation/strategy-comparison/`. Gate 2 (9 cases × 3 runs) must not be
run unless the targeted report says Gate 1 passed. In the recorded Phase 2.2
run, Gate 1 failed due provider timeouts and Gate 2 was `SKIPPED_BY_GATE`.

The final stabilized Phase 2.3 command is:

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
uv run python -m evaluation.strategy_comparison --strategy both --output-dir results/evaluation/strategy-comparison/phase23-gate1
```

It enforces concurrency 1, `num_predict=256`, a 30-second total deadline per
attempt, one retry only for timeout/connection/provider failure, and a bounded
warm-up. A timeout terminates the evaluation child process, closes its client
connection, triggers fallback, and is never counted as pass. Wrong semantic
facts and valid `unknown` results are never retried.

The final comparison was `INCONCLUSIVE` because neither strategy returned a
complete bounded response. Gate 2 was `SKIPPED_BY_GATE`; no full-validation
command should be run for this Phase 2 evidence. Strategy A remains the
production default and Strategy B remains experimental. See
`results/evaluation/strategy-comparison/phase23-stabilization.md` and
`phase2-final-summary.md`.
