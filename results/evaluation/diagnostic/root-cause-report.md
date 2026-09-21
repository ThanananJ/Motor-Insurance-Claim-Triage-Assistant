# Phase 2.1 — Live Output Pipeline Root-cause Report

Diagnostic run: `diagnostic-20260920T021024Z.json`
Model: `qwen2.5:3b`
Prompt version: `focused-prompts-v1`
Runs: 1 per case (root cause was clear; the permitted second run was unnecessary)

## A. Selected Cases

| Case | Prompt | Expected critical field(s) | Selection reason |
|---|---|---|---|
| MODEL-EVENT-002 | event_exclusion | all fields `unknown` | Control case that passed the Phase 2 live baseline |
| MODEL-RISK-001 | history_risk | repeated claims, severe damage, weak evidence = `true` | Explicit critical risk returned as unknown in baseline |
| MODEL-LATE-001 | late_reason | late reason = `true` | Explicit hospitalization reason returned as unknown |
| MODEL-EVENT-001 | event_exclusion | event = collision; illegal racing = `true` | Explicit exclusion plus event-type failure |

All inputs are existing committed synthetic cases. No expected result was changed.

## B. Pipeline Trace

### MODEL-EVENT-002 — control

| Stage | Expected critical value | Observed value | Changed? | Error/Fallback |
|---|---|---|---|---|
| Raw model content | all `unknown` | all `unknown` | No | None |
| LangChain output | all `unknown` | all `unknown` | No | None |
| Parsed dictionary | all `unknown` | all `unknown` | No | None |
| Pydantic model | all `unknown` | all `unknown` | No | None |
| Normalized output | all `unknown` | all `unknown` | No | None |
| Evaluator output | all `unknown` | all `unknown` | No | None |

### MODEL-RISK-001 — critical risk

| Stage | Expected critical value | Observed value | Changed? | Error/Fallback |
|---|---|---|---|---|
| Raw model content | repeated/severe/weak = `true` | all three `unknown` | Model differs from expected | None |
| LangChain output | `true` | `unknown` | No change from raw | None |
| Parsed dictionary | `true` | `unknown` | No | None |
| Pydantic model | `true` | `unknown` | No | Valid |
| Normalized output | `true` | `unknown` | No | None |
| Evaluator output | `true` | `unknown` | No | Correctly reports mismatch |

### MODEL-LATE-001 — explicit valid reason

| Stage | Expected critical value | Observed value | Changed? | Error/Fallback |
|---|---|---|---|---|
| Raw model content | `true` | `unknown` | Model differs from expected | None |
| LangChain output | `true` | `unknown` | No change from raw | None |
| Parsed dictionary | `true` | `unknown` | No | None |
| Pydantic model | `true` | `unknown` | No | Valid |
| Normalized output | `true` | `unknown` | No | None |
| Evaluator output | `true` | `unknown` | No | Correctly reports mismatch |

### MODEL-EVENT-001 — racing exclusion

| Stage | Expected critical value | Observed value | Changed? | Error/Fallback |
|---|---|---|---|---|
| Raw model content | event=`accidental_collision`, racing=`true` | event=`unknown`, racing=`true` | Event differs at generation | None |
| LangChain output | same expected pair | event=`unknown`, racing=`true` | No change from raw | None |
| Parsed dictionary | same expected pair | event=`unknown`, racing=`true` | No | None |
| Pydantic model | same expected pair | event=`unknown`, racing=`true` | No | Valid |
| Normalized output | same expected pair | event=`unknown`, racing=`true` | No | None |
| Evaluator output | same expected pair | event=`unknown`, racing=`true` | No | Correctly reports mismatch |

No field changed to `unknown` after generation in any diagnostic case.

## C. Direct Ollama vs Application Path

Both paths used the same prompt bytes (verified SHA-256), model, JSON schema,
and temperature 0. Application Path used LangChain's streaming
`with_structured_output(method="json_schema")`; Direct Path sent a non-streaming
`/api/chat` request with the same schema. The transport behavior is therefore
comparable but not byte-identical.

| Case | Application raw | Direct raw | Parsed values equal | App wall time | Direct wall time |
|---|---|---|---:|---:|---:|
| MODEL-EVENT-002 | all unknown | all unknown | Yes | 10,120 ms | 3,391 ms |
| MODEL-RISK-001 | all unknown | all unknown | Yes | 3,844 ms | 3,295 ms |
| MODEL-LATE-001 | unknown | unknown | Yes | 2,900 ms | 2,462 ms |
| MODEL-EVENT-001 | event unknown; racing true | same | Yes | 3,808 ms | 3,400 ms |

Raw content was valid JSON in all eight calls. LangChain parsed output,
Pydantic output, normalized output, and evaluator output preserved the raw
values exactly. No adapter/parser/mapping defect was observed.

The direct Ollama envelope supplied real token counts and duration metadata.
Prompt counts ranged from 706–950 tokens and output counts from 13–56 tokens.
These values are retained only in the diagnostic artifact; production metrics
were not changed in this phase.

## D. Timeout Timeline

Application-path diagnostic timeline:

| Case | Client setup | Provider call through response | Parse + validation | Total |
|---|---:|---:|---:|---:|
| MODEL-EVENT-002 | 29 ms | 10,091 ms | <1 ms | 10,120 ms |
| MODEL-RISK-001 | 24 ms | 3,820 ms | <1 ms | 3,844 ms |
| MODEL-LATE-001 | 24 ms | 2,876 ms | <1 ms | 2,900 ms |
| MODEL-EVENT-001 | 24 ms | 3,785 ms | <1 ms | 3,808 ms |

Parsing and Pydantic validation are negligible; provider/model time dominates.
The first application request included approximately 6.19 seconds of Ollama
model loading according to response metadata.

Source inspection confirmed:

- `ChatOllama` defaults to `stream=True`.
- The configured `timeout=60` is passed to `httpx.Client`.
- An httpx scalar timeout limits individual connect/read/write/pool operations;
  it is not a total request deadline. Streaming chunks can reset read activity,
  so total wall time may exceed 60 seconds.
- The installed Ollama client request path contains no automatic retry loop.
- The model evaluator invokes the provider once per case; its measured latency
  includes the complete streamed provider call and fallback classification.

This explains how successful baseline calls reached 112–163 seconds without a
retry. The four baseline timeout exceptions indicate an individual transport
operation exceeded its timeout before a complete response. No case was
successfully received and then incorrectly reclassified as timeout.

## E. Root Cause

### Excessive `unknown` values

- Classification: `MODEL_GENERATION`
- Confidence: **High**
- Evidence: Raw Application and Direct Ollama outputs already contain the same
  incorrect `unknown` values. All downstream stages preserve them unchanged.

### Baseline latency above 60 seconds and timeout variability

- Classification: `TIMEOUT_CONFIGURATION` with provider/model latency
- Confidence: **High** for timeout semantics; **Medium** for the exact source of
  run-to-run latency variability
- Evidence: production path streams; 60 seconds is an httpx operation timeout,
  not an end-to-end deadline. Ollama metadata shows model load/prompt/evaluation
  time dominates, while parsing is below 1 ms. Queue/GPU state during the old
  27-call baseline cannot be reconstructed and remains inconclusive.

### Adapter, parser, validation, normalization, evaluator

- Classification: no defect reproduced
- Confidence: **High** for these four representative cases
- Evidence: exact value equality at every post-generation stage.

## F. Changes Made

- Added `evaluation/diagnostic.py`: development-only, four-case bounded trace
  with prompt hash/length, raw synthetic responses, direct/application paths,
  validation stages, token metadata, and timing.
- Added `tests/test_evaluation_diagnostic.py`: verifies four-case scope,
  response snapshot redaction boundary, and relative timeline calculation.
- Added this report and one machine-readable diagnostic artifact.
- Updated evaluation documentation and handoff.

No production provider/parser behavior was changed because no application bug
was demonstrated. No prompt, model, Policy, schema, expected result, or rule was
changed.

## G. Remaining Unknowns

- The exact cause of old run-to-run provider latency variation is
  `INCONCLUSIVE`; the diagnostic run was warm and completed without timeout.
- This small diagnostic cannot prove adapter correctness for every possible
  malformed response, only for the selected representative outputs.
- Whether non-streaming production calls would reduce tail latency without
  another tradeoff was not tested because transport strategy changes are out of
  Phase 2.1 scope.

## H. Recommendation

Revise the structured-output strategy in a controlled follow-up: compare the
current schema-constrained generation against a minimal JSON instruction path
for the same representative cases, while preserving validation and human
confirmation. The evidence shows that changing parser/Pydantic/evaluator logic
would be the wrong fix because the values are already wrong in raw generation.
