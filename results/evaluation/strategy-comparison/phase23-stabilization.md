# Phase 2.3 Execution Stabilization

## Ollama state

- Ollama `0.34.2`; `qwen2.5:3b` installed.
- Initial `ollama ps` was empty: no model or visible request was loaded before
  the final experiment.
- Comparison execution was sequential (`concurrency=1`).
- After the final run, `qwen2.5:3b` remained loaded. The single permitted reset
  was performed with `ollama stop qwen2.5:3b`; the following `ollama ps` was
  empty.
- Ollama does not expose a detailed request queue through `ollama ps`, so a
  loaded model alone does not prove a queued request. Child termination closed
  each client connection; no force-kill or service restart was used.

## Evaluation-only controls

| Control | Value | Rationale |
|---|---:|---|
| Concurrency | 1 | Prevent overlap between strategies/cases |
| Output bound | `num_predict=256` | Prior structured responses used 13–56 tokens; 256 leaves JSON headroom |
| Total deadline | 30 seconds per attempt | Prior healthy diagnostic calls were 2.5–10.1 seconds |
| Retry | Maximum 1 | Timeout/connection/provider failures only |
| Keep alive | 5 minutes | Avoid intentional unload between sequential calls |
| Temperature | 0 | Match prior evaluation |
| Seed | 42 | Provider accepts it; determinism is not guaranteed |

The deadline is enforced by a spawned child process. On expiration the child is
terminated, closing its client connection; timeout is classified
`PROVIDER_TIMEOUT`, triggers safe fallback, and is never counted as passing.
Semantic mismatches, valid `unknown` outputs, and schema-valid wrong facts are
not retried.

## Verification

Seven targeted unit tests cover sequential order, output bound, total-deadline
termination, bounded retry, timeout classification/fallback, strategy safety
gate behavior, experimental Strategy B, and production-default Strategy A.

These controls affect only `evaluation.strategy_comparison`; the production
Ollama provider and application workflow were not changed.
