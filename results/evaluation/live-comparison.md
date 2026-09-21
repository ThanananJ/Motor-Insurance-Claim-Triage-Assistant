# Phase 2 Live Model Comparison

Model: `qwen2.5:3b` via Ollama `0.34.2` at `http://localhost:11434`
Dataset: `1.0.0`
Policy: `policy-5.1` (unchanged)

## Decision

Prompt tuning round 1 (`focused-prompts-v2`) was **rejected**. It improved some
aggregate measurements, but introduced an unsupported critical exclusion fact
in all three prompt-injection runs. Production prompts were restored to
`focused-prompts-v1`.

| Metric | Baseline v1 | Candidate v2 | Change | Gate / decision |
|---|---:|---:|---:|---|
| Field F1 | 0.7226 | 0.7468 | +0.0242 | Still below 0.85 |
| Schema validity | 85.19% (23/27) | 92.59% (25/27) | +7.40 pp | Still below 95% |
| Critical exclusion recall | 66.67% (4/6) | 83.33% (5/6) | +16.66 pp | Still below 100% |
| Critical risk recall | 0% (0/12) | 0% (0/12) | none | FAIL |
| Unsupported facts | 0/99 | 3/99 | +3 | Safety regression — reject |
| Exact output consistency | 77.78% (7/9) | 77.78% (7/9) | none | Informational |
| Average latency | 40,057 ms | 18,610 ms | -21,447 ms | Improved |
| P50 latency | 31,719 ms | 2,085 ms | -29,634 ms | Improved |
| P95 latency | 112,105 ms | 98,808 ms | -13,297 ms | Improved |

The unsupported facts were `alcohol_or_drug_involvement=true` for the
prompt-injection case, despite no alcohol evidence. Because this could trigger a
Policy exclusion, the candidate cannot be accepted even though other metrics
improved.

## Baseline Failure Summary

- Event/exclusion: two timeouts, missed event type for racing, and event type
  mismatch in the prompt-injection case; critical exclusion recall 4/6.
- History/risk: the model returned all `unknown` for explicit repeated claims,
  severe damage, weak evidence, and conflicting statements; critical recall
  0/12.
- Late reason: explicit valid and absent reasons were usually returned as
  `unknown`; accuracy 1/9, with two timeouts on the unknown case.
- Provider: 4/27 timeouts; every failure remained a failed/skipped invocation
  and was never counted as a pass.

## Live Service-level E2E

The accepted v1 prompts were used. Result: **PARTIAL**.

- AI extraction field accuracy: 15.38% (8/52)
- Fully matching AI proposal: 1/10 cases
- Post-confirmation exact routing: 100% (10/10)
- Coverage status: 100% (10/10)
- Missing-document detection: 100% (10/10)
- Human-confirmation boundary: 100% (10/10)

Expected synthetic confirmed facts simulated the Claim Officer correction step;
they were kept separate from model proposals. Therefore correct post-confirmation
routing does not conceal poor extraction quality.
