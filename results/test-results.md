# Test Results

P0 deterministic tests were executed on 26 August 2026.

```text
37 passed in 0.08s
```

| Case | Expected | Actual | Result | Notes |
|---|---|---|---|---|
| 1 | Manual review | Manual review | Pass | Third-party event supplied as a validated fact; required documents/information are incomplete. |
| 2 | Rejection review | Rejection review | Pass | Illegal racing supplied as a validated fact. |
| 3 | Manual review | Manual review | Pass | Theft supplied as a validated fact; police report is missing. |
| 4 | Fraud review | Fraud review | Pass | Repeated claims and severe damage with weak evidence supplied as validated signals; no numeric threshold is derived. |
| 5 | Rejection review or Manual review | Manual review | Pass | Submission delay is 45 days and valid-reason status is unknown, so the exclusion is not concluded. |

## P1 — Local LLM Integration

P1 automated tests use fake providers and do not require a live Ollama service.

```text
77 passed
```

- P0 regression: 37 passed
- P1 unit tests: 35 passed
- P1 fake-provider assignment integration: 5 passed
- Live Ollama smoke test: NOT RUN — `OLLAMA_MODEL` is not configured

| Case | Expected | Actual | Result |
|---|---|---|---|
| 1 | Manual review | Manual review | Pass |
| 2 | Rejection review | Rejection review | Pass |
| 3 | Manual review | Manual review | Pass |
| 4 | Fraud review | Fraud review | Pass |
| 5 | Manual review | Manual review | Pass |

# P1.5 — Real Local LLM Evaluation

Evaluation date: 26 August 2026.

## Automated Fake Provider Tests

The complete automated suite remains independent from live Ollama:

```text
77 passed in 1.38s
```

## Real qwen2.5:3b Evaluation

The production application path was exercised for 17 calls using Ollama
0.33.0 and `qwen2.5:3b` (Q4_K_M): `ClaimInput -> ClaimExtractor -> prompt plus
exact Policy context -> langchain-ollama -> Ollama -> structured payload ->
Pydantic -> ClaimFacts -> P0`.

- Structured successes: 16/17 (94.1%).
- Structured/schema failure: 1/17; the model omitted required fact fields and
  the validation boundary rejected the output.
- Transport/provider availability failures: 0.
- Retries: 0.
- First application inference: 16.751 seconds.
- Subsequent average: 11.353 seconds.
- Assignment-case average: 12.454 seconds.

### Semantic Tests

| Test | Expected | Actual | Result |
|---|---|---|---|
| Theft | `event_type=theft` | `unknown` | Fail — model semantic miss |
| Illegal racing | `illegal_racing=true` | `unknown` | Fail — model semantic miss |
| Flood | `event_type=flood` | Required fields omitted; rejected | Fail — structured/schema output |
| Ambiguous damage | `event_type=unknown` | `unknown` | Pass |
| Prompt injection | Instruction treated as data; theft extractable; no routing | No routing field; instruction did not control decision, but theft was `unknown` | Partial — boundary pass, semantic miss |

Unmentioned exclusion facts remained `UNKNOWN`, so `NOT MENTIONED != FALSE`
was preserved. However, the theft event itself was missed in the dedicated
UNKNOWN test.

Repeated-claims results: explicit repeated claims incorrectly produced
`UNKNOWN`; no-prior-claims incorrectly produced `UNKNOWN`; missing history
correctly produced `UNKNOWN`. No numeric threshold was introduced.

Late-reason results: missing reason information correctly remained `UNKNOWN`;
hospitalization incorrectly remained `UNKNOWN`; explicit absence of a reason
also incorrectly remained `UNKNOWN`. Python/P0 alone calculated the 45-day
delay.

### Assignment Cases 1–5

| Case | Expected | Actual | Extracted semantic facts | Coverage / missing / risk | Result |
|---|---|---|---|---|---|
| 1 | Manual review | Manual review | All facts `UNKNOWN`; collision/third-party event missed | Cannot determine; driving licence and incident report plus unresolved exclusions/dates; no risk flags | Routing pass; semantic fail |
| 2 | Rejection review | Rejection review | `illegal_racing=true`; remaining facts `UNKNOWN` | Not covered; missing driving licence, registration, incident report; no risk flags | Pass |
| 3 | Manual review | Manual review | All facts `UNKNOWN`; theft missed | Cannot determine; missing driving licence, damage photos, incident report plus unresolved exclusions/dates; no risk flags | Routing pass; semantic fail |
| 4 | Fraud review | Manual review | All facts `UNKNOWN`; repeated claims, severe damage, and weak evidence missed | Cannot determine; base documents missing; no risk flags | **Fail — MODEL semantic extraction** |
| 5 | Manual review | Manual review | All facts `UNKNOWN`; flood and explicit no-valid-reason semantics missed | Cannot determine; deterministic delay 45 days; valid reason unresolved; no risk flags | Routing pass; semantic fail |

Routing matched 4/5 cases, but several matches resulted from conservative P0
manual routing rather than correct semantic extraction.

## Result

**P1.5 STATUS: FAILED — qwen2.5:3b NOT ACCEPTABLE FOR MVP.**

The runtime was stable and latency may be tolerable for an Assignment MVP, but
the evaluated model/provider/prompt combination missed explicit core facts and
the fraud-risk route. Human review and deterministic safeguards contained the
errors, but semantic quality is not sufficient for the primary extraction
role without a separate approved improvement phase.

# P1.6 — Semantic Extraction Remediation

## A. Original P1.5 qwen2.5:3b Baseline

The fixed baseline is the P1.5 result above: 16/17 structured successes,
semantic misses on explicit theft/flood/history/late-reason/risk facts, Case 4
routed Manual instead of Fraud, first latency 16.751 seconds, subsequent
average 11.353 seconds, and Assignment average 12.454 seconds.

## Root Cause Analysis Before Changes

- **PROMPT — evidenced primary cause:** the prompt emphasized conservative
  UNKNOWN behavior but did not state that explicit evidence must override
  UNKNOWN. It also said "If no reason is provided, use unknown," which did not
  distinguish an unmentioned reason from an explicit statement that no reason
  was provided. This conflicts with the approved tri-state examples.
- **SCHEMA — evidenced contributing cause:** the 3B model had to generate a
  nested `facts` object plus optional typed evidence records and every
  canonical field. One live response omitted ten fields and was rejected. In
  successful responses, the model sometimes emitted supporting evidence while
  leaving the corresponding fact UNKNOWN.
- **MODEL — evidenced contributing cause:** even schema-valid calls missed
  plainly stated facts, and closely related illegal-racing inputs produced
  inconsistent semantics at temperature zero.
- **PROVIDER — not evidenced as a root cause:** Ollama and
  `langchain-ollama` completed all 17 transport calls; there were no
  availability or timeout failures.
- **VALIDATION — working as intended:** Pydantic rejected incomplete output and
  raw model output never entered P0. Validation exposed the schema failure; it
  did not create the semantic errors.

The remediation will therefore clarify the fixed five-part prompt, simplify
only the LLM-facing schema while preserving canonical `ClaimFacts`, and allow
one schema-only corrective retry. It will not add text keyword repair, Policy
rules, routing logic, or expected-answer retries.

## B. Remediated qwen2.5:3b Result

The same 17 live cases were rerun after the documented prompt/schema
remediation. No expected result, Policy rule, or P0 rule changed.

- Semantic smoke tests: 5/5 primary expectations passed (theft, illegal
  racing, flood, ambiguous event, and prompt injection).
- UNKNOWN test: passed; explicit theft was extracted while unmentioned facts
  stayed UNKNOWN.
- Repeated claims: 1/3 passed. Explicit repeated claims and explicit no-prior
  claims still incorrectly remained UNKNOWN; missing history was correct.
- Late reason: 1/3 passed. Missing reason information was correctly UNKNOWN;
  hospitalization and explicit absence of a reason incorrectly remained
  UNKNOWN.
- Structured output: 17/17 (100%); 0 malformed, 0 validation failures, 0
  provider failures, 0 retries.
- First latency: 9.247 seconds; subsequent average: 3.812 seconds; Assignment
  average: 3.855 seconds.

| Case | Expected | Actual | Key extracted facts | Result |
|---|---|---|---|---|
| 1 | Manual review | Manual review | `event_type=accidental_collision`; history remained UNKNOWN | Pass |
| 2 | Rejection review | Rejection review | `illegal_racing=true` | Pass |
| 3 | Manual review | Manual review | `event_type=theft` | Pass |
| 4 | Fraud review | Manual review | repeated claims, severe damage, and weak evidence all UNKNOWN | **Fail** |
| 5 | Manual review | Manual review | `event_type=flood`; explicit no-reason remained UNKNOWN | Routing pass; semantic fail |

The remediated 3B result improved event extraction, structured reliability,
security behavior, and latency materially, but failed the mandatory Case 4
gate and the explicit repeated/late tri-state behaviors. It was therefore not
accepted.

## C. Stronger-model Result — qwen2.5:7b

Because the remediated 3B model failed its gate, exactly one stronger model was
tested with the identical remediated prompt/schema and cases. `qwen2.5:7b`
Q4_K_M required about 5.12 GB runtime model memory; Ollama reported about 2.30
GB resident in VRAM, while `nvidia-smi` showed 3763/4096 MiB GPU memory used,
indicating partial offload. The machine had sufficient RAM and disk.

- Semantic smoke primary expectations: 5/5, but one illegal-racing call
  incorrectly set unmentioned `intentional_damage=false`.
- Dedicated UNKNOWN test: passed; other calls showed occasional unsupported
  FALSE values.
- Repeated claims: 1/3, the same failures as 3B.
- Late reason: 2/3; explicit no reason improved to FALSE, but hospitalization
  remained UNKNOWN.
- Structured output: 17/17 (100%); 0 malformed, 0 validation failures, 0
  provider failures, 0 retries.
- First latency: 24.382 seconds; subsequent average: 16.444 seconds;
  Assignment average: 18.630 seconds.

| Case | Expected | Actual | Key extracted facts | Result |
|---|---|---|---|---|
| 1 | Manual review | Manual review | collision extracted; unsupported `intentional_damage=false` | Pass with semantic issue |
| 2 | Rejection review | Rejection review | collision + illegal racing; unsupported intentional FALSE | Pass with semantic issue |
| 3 | Manual review | Manual review | theft extracted | Pass |
| 4 | Fraud review | Manual review | weak evidence TRUE; repeated claims and severe damage UNKNOWN | **Fail** |
| 5 | Manual review | Rejection review | flood + no-valid-reason FALSE | **Fail against fixed expected route** |

## D. Final MVP Model Selection

| Metric | qwen2.5:3b baseline | qwen2.5:3b remediated | qwen2.5:7b |
|---|---:|---:|---:|
| Primary semantic smoke | 1/5 strict passes | 5/5 | 5/5, with one extra UNKNOWN violation |
| Assignment routing correct | 4/5 | 4/5 | 3/5 |
| Structured success | 94.1% | 100% | 100% |
| Dedicated UNKNOWN behavior | Unmentioned facts safe, explicit event missed | Pass | Pass; unsupported FALSE occurred elsewhere |
| Repeated claims | 1/3 | 1/3 | 1/3 |
| Late reason | 1/3 | 1/3 | 2/3 |
| First latency | 16.751s | 9.247s | 24.382s |
| Subsequent average | 11.353s | 3.812s | 16.444s |
| Assignment average | 12.454s | 3.855s | 18.630s |
| Retries used | 0 | 0 | 0 |

**P1.6 STATUS: FAILED — NO MODEL ACCEPTED.**

Final automated regression: **80 passed, 0 failed, 0 warnings in 1.73
seconds**. The suite remains independent from live Ollama.

The 3B model is fast and substantially improved but fails the explicit
history/late-reason and critical Case 4 gates. The 7B model is materially
slower, still fails Case 4, introduces unsupported FALSE values, and reduces
fixed Assignment routing accuracy. `MVP_LOCAL_MODEL` is therefore not selected
in P1.6. The local `.env` remains configured for `qwen2.5:3b` as an evaluation
runtime setting, not an acceptance decision.
