# Phase 2.2 — Targeted Structured-output Strategy Comparison

## Configuration and fairness controls

- Model: `qwen2.5:3b`
- Endpoint: `http://localhost:11434`
- Dataset and expected results: unchanged version `1.0.0`
- Policy and focused prompt semantics: unchanged, `focused-prompts-v1`
- Pydantic schemas: identical for both strategies
- Temperature: 0
- Seed: 42 (provider acceptance recorded; determinism is not guaranteed)
- Context size: provider default
- Warm-up: successful recorded warm-up, 10,044 ms, excluded from latency
- Execution order: A/B alternated by case

An earlier warm-up attempt timed out before comparison started and produced no
case result. The CLI was corrected to record warm-up failure without aborting a
whole experiment. The recorded comparison then completed all eight targeted
invocations.

## Strategies

- **A — current:** unchanged production path using LangChain streaming and
  schema-constrained `json_schema` structured output.
- **B — minimal-json:** experimental-only path using the same focused prompt,
  an additional concise JSON-only formatting instruction, Ollama `format=json`,
  manual JSON parsing, and the same Pydantic schema.

Production default remained Strategy A throughout.

## Gate 1 results

| Case | Field | Expected | Strategy A | Strategy B |
|---|---|---|---|---|
| Control | all five fields | `unknown` | timeout / no output | timeout / no output |
| Risk | `repeated_claims` | `true` | timeout / no output | timeout / no output |
| Risk | `severe_damage` | `true` | timeout / no output | timeout / no output |
| Risk | `weak_evidence` | `true` | timeout / no output | timeout / no output |
| Late | `late_submission_valid_reason` | `true` | timeout / no output | timeout / no output |
| Event | `illegal_racing` | `true` | `true` | timeout / no output |
| Event | `event_type` | `accidental_collision` | `unknown` | timeout / no output |

| Metric | Strategy A | Strategy B |
|---|---:|---:|
| Successful invocations | 1/4 | 0/4 |
| JSON valid | 1/4 | 0/4 |
| Pydantic valid | 1/4 | 0/4 |
| Critical risk fields correct | 0/3 | 0/3 |
| Late-reason correct | 0/1 | 0/1 |
| Event/exclusion fields correct | 1/2 | 0/2 |
| Observed unsupported critical facts | 0 | 0, but all B calls were unassessable |
| Fallback/provider error | 3/4 | 4/4 |

All seven failed case invocations raised `ReadTimeout` after approximately
62.1 seconds. The successful current-strategy event invocation took 230.1
seconds, demonstrating again that the scalar read timeout is not a total request
deadline during an active stream.

## Gate 1 decision

**FAIL**

- Risk did not improve.
- Event/exclusion was worse because Strategy B produced no assessable output.
- Strategy B failed JSON/Pydantic validity in all four targeted calls because no
  complete response was received.
- Control hallucination and unsupported-critical-fact safety could not be fully
  assessed for Strategy B; absence of output is not counted as safety success.
- No final-decision field or human-boundary violation was observed.

## Gate 2

`SKIPPED_BY_GATE`

Running 27 additional invocations would violate the progressive gate and would
not resolve the provider instability demonstrated by Gate 1.
