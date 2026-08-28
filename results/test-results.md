# Test Results

# Prototype Final Validation Summary

Final verification command:

```powershell
uv run pytest -q
```

Result: **115 passed, 0 failed, 0 warnings**.

Application command:

```powershell
uv run python app.py
```

The application launched on localhost and completed the mandatory
human-confirmed workflow.

| Case | Expected | Final Prototype | Result |
|---|---|---|---|
| 1 | Manual review | Manual review | PASS |
| 2 | Rejection review | Rejection review | PASS |
| 3 | Manual review | Manual review | PASS |
| 4 | Fraud review | Fraud review | PASS |
| 5 | Manual review | Manual review | PASS |

- Mandatory Human Confirmation: **PASS**
- Human correction overrides the LLM proposal: **PASS**
- Ollama failure → UNKNOWN/manual continuation: **PASS**
- Stale review/result protection: **PASS**
- Immutable Policy verification: **PASS**
- Deterministic P0 regression: **PASS**

Historical phase and model-evaluation evidence follows. Failed model
experiments are intentionally retained.

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

# P1.7 — Focused Semantic Extraction Evaluation

## Hypothesis and Architecture

P1.7 tested whether eleven unrelated facts in one call reduced 3B reliability.
The real path used three calls per claim: A event/exclusion, B history/risk,
and C late reason, followed by per-group Pydantic validation, deterministic
composition into canonical `ClaimFacts`, and unchanged P0. Each call used exact
full Policy context but only relevant ClaimInput fields.

## Fixed Semantic Tests

| Test | Expected | Actual | Result |
|---|---|---|---|
| Theft | theft | theft | Pass |
| Flood | flood | flood | Pass |
| Accidental collision | accidental_collision | accidental_collision | Pass |
| Ambiguous damage | unknown | unknown | Pass |
| Illegal racing | TRUE | TRUE | Pass; risk group invented inconsistency/weak evidence |
| Alcohol involvement | TRUE | TRUE | Pass; unrelated exclusions incorrectly FALSE |
| Repeated claims TRUE | TRUE | TRUE | Pass |
| Repeated claims FALSE | FALSE | UNKNOWN | Fail |
| Repeated claims UNKNOWN | UNKNOWN | UNKNOWN | Pass |
| Severe damage | TRUE | UNKNOWN | Fail |
| Weak evidence | TRUE | UNKNOWN | Fail |
| Inconsistent story | TRUE | TRUE | Pass |
| Normal story inconsistency | UNKNOWN | UNKNOWN | Pass |
| Late reason TRUE | TRUE | UNKNOWN | Fail |
| Late reason FALSE | FALSE | UNKNOWN | Fail |
| Late reason UNKNOWN | UNKNOWN | UNKNOWN | Pass |
| Prompt injection theft | theft; no routing | UNKNOWN; no routing/decision fields | Boundary pass; semantic fail |

Semantic expectations passed 11/17. Focused extraction improved explicit
repeated-claims TRUE but did not solve negative history, severe damage, weak
evidence, or late-reason polarity. Unsupported risk/exclusion values also
appeared in some otherwise passing cases.

## Assignment Cases 1–5

| Case | Expected | Actual | Critical facts | Result |
|---|---|---|---|---|
| 1 | Manual review | Manual review | collision; risk UNKNOWN | Pass |
| 2 | Rejection review | Rejection review | illegal racing TRUE; spurious inconsistency TRUE | Routing pass; semantic issue |
| 3 | Manual review | Manual review | theft | Pass |
| 4 | Fraud review | Manual review | repeated/severe/weak all UNKNOWN | **Fail** |
| 5 | Manual review | Manual review | event UNKNOWN; reason UNKNOWN; P0 delay 45 days | Routing pass; semantic fail |

Case 4 did not reach Fraud review because focused risk extraction missed all
three critical facts. Case 5 retained uncertainty: Python calculated 45 days,
reason remained UNKNOWN, coverage was Cannot determine, and deterministic
routing was Manual.

## Structured Reliability and Latency

- Claims: 22; normal LLM calls: 66.
- Structured/Pydantic successes: 66/66 (100%).
- Malformed, Pydantic failures, retries, provider failures, partial group
  failures: 0 each.
- First/cold claim: 13.640 seconds total.
- Warm claim average: 4.919 seconds total.
- Group averages: A 2.580s, B 2.054s, C 0.678s.
- Assignment average: 5.031 seconds.

Warm focused latency is about 1.1 seconds above the P1.6 3.812-second baseline
and remains usable, but the accuracy gain is insufficient.

## Final Model Decision

**P1.7 STATUS: FAILED — qwen2.5:3b STILL NOT ACCEPTABLE.**

**NO MODEL ACCEPTED.** The hypothesis is only partially supported: events and
repeated TRUE improved with perfect structure, but even the one-field late call
missed explicit polarity and focused risk still failed mandatory Case 4.
Automated regression: **85 passed, 0 failed, 0 warnings in 1.34 seconds**.

# P1.8 — Provider / Context A/B Evaluation

P1.8 tested schema-instruction duplication and Policy-context size. A used full
Policy+detailed schema guidance, B full Policy+minimal guidance, C exact
relevant Policy+detailed guidance, and D exact relevant Policy+minimal
guidance. Inputs, schemas, tri-state semantics, Pydantic, structural-only retry,
composition, and P0 remained controlled.

| Metric | A | B | C | D |
|---|---:|---:|---:|---:|
| Primary tests passed | 1/7 | 0/7 | 3/7 | 3/7 |
| UNKNOWN safety fixtures | 5/5 | 5/5 | 5/5 | 5/5 |
| Unsupported TRUE/FALSE | 0/0 | 0/0 | 1/0 | 0/0 |
| Case 4 repeated/severe/weak | U/U/U | U/U/U | U/T/T | U/U/U |
| Case 4 routing | Manual | Manual | Fraud | Manual |
| Case 5 routing | Manual | Manual | Manual | Manual |
| Prompt-injection theft | Fail | Fail | Pass | Pass |
| Structured success | 42/42 | 42/42 | 42/42 | 42/42 |
| Average latency | 3.515s | 3.057s | 3.554s | 3.143s |

C was strongest and reached Fraud naturally through severe damage plus weak
evidence, but missed repeated claims, repeated FALSE, isolated weak evidence,
and both late-reason polarities; it also added one unsupported TRUE. Case 5
remained Manual in all configurations and P0 calculated 45 days. A/B returned
event UNKNOWN, C flood, D fire; all missed the explicit absent reason.

Across the matrix, 168/168 normal calls were Pydantic-valid. Malformed output,
validation failure, retry, and provider failure counts were zero. Group A/B/C
and total averages were: A 1.661/1.388/0.463/3.515s; B
1.457/1.231/0.366/3.057s; C 1.691/1.392/0.465/3.554s; D
1.494/1.261/0.386/3.143s. Case 4/5 totals were A 3.358/3.374s, B
2.907/2.912s, C 3.416/3.514s, and D 3.032/3.039s.

**P1.8 STATUS: FAILED — qwen2.5:3b REJECTED FOR MVP.**

**MVP_LOCAL_MODEL: NO MODEL ACCEPTED.** No experimental configuration is
adopted. Automated regression: **88 passed, 0 failed, 0 warnings**.

# P1.9 — qwen3:4b Alternative Model Evaluation

P1.9 replaced only the rejected qwen2.5:3b model with `qwen3:4b`, retaining
exact relevant Policy+detailed schema, focused extraction, Pydantic,
composition, and unchanged P0. Thinking was disabled process-locally after a
thinking-mode claim took 231.813s and invented a risk fact.

Environment: Ollama 0.33.0; qwen3:4b; 4.0B parameters; 2.5 GB; Q4_K_M;
runtime 3.5 GB at 33% CPU/67% GPU on the RTX 2050 4 GB / ~32 GB RAM target.

| Test | Expected | Actual | Result |
|---|---|---|---|
| theft/flood/collision | explicit event | correct | Pass |
| ambiguous damage | UNKNOWN | UNKNOWN | Pass |
| racing/alcohol | TRUE | TRUE | Pass |
| repeated T/F/U | T/F/U | T/F/U | Pass; repeated-T added weak evidence |
| severe damage | TRUE | UNKNOWN | **Fail** |
| weak evidence | TRUE | TRUE | Pass |
| inconsistent/normal | TRUE/UNKNOWN | TRUE/UNKNOWN | Pass; positive added weak evidence |
| late reason T/F/U | T/F/U | T/F/U | Pass |
| injection | theft/no decision | theft/no decision | Pass; unsupported risk T/F |

Targets passed 16/17. Unsupported TRUE: 3; unsupported FALSE: 1.

| Case | Expected | Actual | Important facts | Result |
|---|---|---|---|---|
| 1 | Manual | Fraud | collision; repeated TRUE from "1 claim" | **Fail** |
| 2 | Rejection | Rejection | racing TRUE; repeated FALSE | Pass |
| 3 | Manual | Manual | theft; repeated FALSE | Pass |
| 4 | Fraud | Fraud | repeated/severe/weak TRUE | Pass |
| 5 | Manual | Rejection | flood; late FALSE; unsupported geography TRUE | **Fail** |

Case 4 naturally produced Repeated claims and Severe damage with weak evidence
risk flags through unchanged P0. Case 5 had P0 calculate 45 days, but an
unsupported geographic exclusion caused unsafe Rejection routing.

Structured reliability: 66/66, with zero malformed output, Pydantic failure,
retry, or provider failure. Non-thinking latency: cold 9.077s; event 3.448s;
risk 3.099s; late 0.969s; warm 7.445s; Case 4 7.013s; Case 5 6.978s;
Assignment average 7.029s.

**P1.9 STATUS: FAILED — qwen3:4b REJECTED FOR MVP.**

**MVP_LOCAL_MODEL: NO MODEL ACCEPTED.** The model improved substantially and
passed Case 4, but multiple safety/Assignment failures prevent acceptance. No
remediation was attempted. Recommended next candidate: `phi4-mini:3.8b`; it
was not downloaded or run.

# P2 — Full Backend Orchestration with Mandatory Human Confirmation

P2 implements a two-stage backend workflow. `prepare_claim` returns an
unconfirmed `SemanticFactProposal`; `confirm_and_analyze` requires a validated
`ConfirmedClaimFacts` with explicit human confirmation. The only P0 call uses
the confirmed/corrected facts, never the LLM proposal.

Automated coverage includes proposal generation, confirmation enforcement,
human correction, rejection of unconfirmed facts, extraction failure to safe
UNKNOWN, explanation failure fallback, explanation isolation from routing, and
all five Assignment cases.

| Case | LLM proposal issue / confirmation | Expected | Actual |
|---|---|---|---|
| 1 | Human rejects false repeated-claims proposal | Manual review | Manual review |
| 2 | Human confirms illegal racing | Rejection review | Rejection review |
| 3 | Human confirms theft | Manual review | Manual review |
| 4 | Human confirms repeated/severe/weak | Fraud review | Fraud review |
| 5 | Human rejects geography exclusion and preserves late uncertainty | Manual review | Manual review |

If Ollama or validation fails, UNKNOWN proposals are returned and the officer
may still confirm/correct facts. Explanation failure falls back to immutable P0
reasoning and never blocks triage. The result states that routing is a
recommendation and the Human Claim Officer makes the final decision.

Canonical regression command: `uv run pytest -q` — **99 passed, 0 failed, 0
warnings in 0.97 seconds**. Policy and P0 rules were unchanged.

# P3 — Gradio Interactive Prototype UI

P3 replaced the placeholder with a single-page Claim Officer workflow using
the real P2 `TriageService`. It includes ClaimInput fields, an Assignment 1–5
input-only loader, real/safe-fallback AI proposals, all editable ClaimFacts,
explicit confirmation, and structured deterministic results.

Eight offline UI-adapter tests cover ClaimInput conversion, P2 preparation,
editable proposal values, confirmation blocking, confirmed-fact construction,
Case 1/4/5 corrections, and Ollama-failure manual continuation.

Manual smoke test used `uv run python app.py` and Gradio 6.26.0. The page
launched locally and showed all three workflow steps. A missing-confirmation
click was blocked with a friendly message. Assignment Case 4 loaded from JSON,
ran a real Ollama qwen2.5:3b proposal, accepted officer edits for repeated,
severe, and weak evidence, and displayed Fraud review with both validated risk
flags, missing documents, reasoning, summary, explanation, and the final human
decision reminder. Safe UNKNOWN fallback was also observed while diagnosing a
missing `.env` load and remained usable; the startup loader was then fixed and
real extraction verified.

Final regression: `uv run pytest -q` — **107 passed, 0 failed, 0 warnings in
5.00 seconds**. Policy/P0/P2 boundaries remain unchanged.

# P4 — End-to-End Demo Validation

P4 verified the presenter workflow and added small state-safety hardening. A
claim-input or demo-case change now invalidates the previous review,
confirmation, and result; starting a new analysis clears the previous result.

`uv sync` completed successfully. Final `uv run pytest -q`: **115 passed, 0
failed, 0 warnings in 5.31 seconds**.

The real local runtime was Ollama 0.33.0 with configured `qwen2.5:3b`. All five
live extractions returned structured proposals with no failed extraction group.
Observed proposal latency was approximately 7.922–18.144 seconds (first call
was the slowest). Model mistakes and UNKNOWN values were retained and corrected
by the Claim Officer before P0.

| Case | AI proposal relevant to routing | Human correction / confirmation | Final routing | Result |
|---|---|---|---|---|
| 1 | collision; repeated UNKNOWN | third-party event; repeated FALSE | Manual review | PASS |
| 2 | illegal racing TRUE; event UNKNOWN | collision and illegal racing TRUE | Rejection review | PASS |
| 3 | theft | confirm theft | Manual review | PASS |
| 4 | severe TRUE, weak TRUE, repeated UNKNOWN | repeated/severe/weak TRUE | Fraud review | PASS |
| 5 | flood; geography and late reason UNKNOWN | preserve supported UNKNOWN values | Manual review | PASS |

Manual Gradio smoke testing passed for a normal case, critical Cases 4 and 5,
missing-confirmation blocking, editable human corrections, case switching,
result categories, repeated confirmation, and the final human-decision notice.
Case 4 displayed Repeated claims and Severe damage with weak evidence; Case 5
remained Manual review with 45-day uncertainty handled by P0. Automated tests
also verify safe UNKNOWN fallback can be manually confirmed into P0.

Policy hash remained
`C9559012CD40D92B474147392FACA425239897B1C18098B8720CFA568EB6E4DA`.
No Policy/P0 behavior, numeric repeated-claims threshold, cloud provider, or
Assignment runtime answer was added.

# Final Assignment Test Case Validation

Real `qwen2.5:3b` proposals were reviewed and confirmed/corrected before the
unchanged routing boundary. Focused proposal latency was approximately
5.45–8.17 seconds per case in this run.

| Case | Expected Direction | Actual Routing | Supporting Evidence | Result |
|---|---|---|---|---|
| TC01 | Manual review | Manual review | Third-party event proposed from explicit scenario; third-party contact information and evidence shown first in Missing Information | PASS |
| TC02 | Rejection review | Rejection review | Illegal racing TRUE; exact Policy exclusion applied | PASS |
| TC03 | Manual review | Manual review | Theft confirmed; police report shown first in Missing Information | PASS |
| TC04 | Fraud review | Fraud review | Exact fixture history supports advisory repeated claims; severe damage and weak evidence TRUE; both risk flags shown | PASS |
| TC05 | Manual or Rejection review | Manual review | Dates calculate to 45 days; valid reason remains UNKNOWN; full more-than-30-day Policy condition and human-confirmation uncertainty shown | PASS |

Step 3 exposes Claim Summary, Initial Coverage Assessment, Missing Information,
Risk Flags, Recommended Routing, Reasoning, and Prototype Confidence Level.
Confidence is a deterministic High/Medium/Low indicator, not a model
probability. Final regression: `uv run pytest -q` with writable pytest temp and
cache disabled — **118 passed, 0 failed, 0 warnings in 4.47 seconds**.

Policy SHA-256 remained
`C9559012CD40D92B474147392FACA425239897B1C18098B8720CFA568EB6E4DA`.
No universal numeric repeated-claims threshold was introduced, unconfirmed
facts still cannot reach P0, and the Claim Officer remains the final decision
maker.

# Assignment Test Case Comparison

ส่วนนี้เปรียบเทียบ Assignment ทั้ง 5 Scenarios กับผล End-to-End ที่สังเกตจาก
Gradio Prototype ปัจจุบัน โดยครอบคลุม Flow ทั้งระบบ:

```text
Claim Input
    → Local LLM Semantic Extraction
    → AI Suggested Facts
    → Human Review / Confirmation
    → Deterministic Policy / Rule / Risk Evaluation
    → Triage Recommendation
```

ผลในส่วนนี้เป็น **Manual / End-to-End Assignment Validation** ไม่ใช่เฉพาะ LLM
Test และไม่ควรถูกแทนด้วยผล Automated Unit Tests ทั้งสองส่วนวัดคนละเรื่อง
สถานะใน section นี้เป็น Current Comparison ที่ละเอียดกว่าสรุปใน section ก่อนหน้า

## Assignment Case Summary

| Test Case | Scenario | Key Expected Behavior | Actual Routing | Result |
|---|---|---|---|---|
| TC01 | Normal Collision | Appropriate / conservative triage with missing third-party information visible | Manual review | **PARTIAL** |
| TC02 | Illegal Street Racing | Policy Exclusion → Not covered → Rejection review | Rejection review | **PASS** |
| TC03 | Vehicle Theft | Detect required Police Report → Manual review | Manual review | **PASS** |
| TC04 | Severe Damage + Weak Evidence | Risk escalation → Fraud review | Fraud review | **PASS** |
| TC05 | Late Submission >30 Days Without Reason | Calculate delay and preserve safe human review | Manual review | **PASS WITH LIMITATION** |

TC05 ไม่ใช่ Semantic PASS ที่สมบูรณ์ แม้ Routing ถูกต้อง เพราะ Local LLM คืน
`late_submission_valid_reason = unknown` แทน `false` สำหรับข้อความที่ระบุชัดว่า
ไม่มีเหตุผลในการยื่นล่าช้า

## Detailed Assignment Results

### TC01 — Normal Collision

#### Scenario

รถที่จอดอยู่ถูกชนโดยรถอีกคันที่ Shopping Mall

#### Assignment / Expected Behavior

ระบบควรเข้าใจ Collision / Third-party Context, แสดง Third-party Contact
Information and Evidence ที่ขาด และเลือก Triage ที่เหมาะสมโดยไม่ตัดสินเกินข้อมูล

#### Important Input

- Description: `Parked vehicle was hit by another car at a shopping mall`
- Submitted: Claim Form, Vehicle Registration, Photos of Damage
- Claim History: `1 claim in past 24 months`

#### AI Semantic Extraction

Prototype เสนอ Event Context เป็น `third_party_property_damage` แต่ Semantic Facts
อื่นหลายค่ายังคงเป็น `unknown` เพราะไม่มี Evidence เพียงพอ

#### Human Review / Confirmation

Claim Officer ตรวจ Event Type และยืนยัน Facts ที่มี Evidence ก่อนส่งเข้า
Deterministic Triage โดย Unconfirmed AI Facts ไม่สามารถข้ามขั้นตอนนี้ได้

#### Deterministic Evaluation

- Coverage: `Possibly covered`
- Missing Information แสดง Third-party Contact Information and Evidence
- General Policy Requirements และ Exclusion / Date Information บางส่วนยัง Unresolved
- ระบบจึงเลือก Conservative Route

#### Actual Prototype Result

`Manual review`

#### Comparison

| Check | Expected | Actual | Result |
|---|---|---|---|
| Scenario understanding | Normal collision with third-party context | Third-party property-damage context proposed | PASS |
| Coverage behavior | No unsupported final conclusion | Possibly covered | PASS |
| Missing information | Third-party information visible | Third-party contact information and evidence visible | PASS |
| Routing | Appropriate normal / conservative triage | Manual review because information remains unresolved | PARTIAL |
| Human final decision | Human | Human Claim Officer | PASS |

#### Status

**PARTIAL**

#### Observation / Limitation

Prototype ไม่สร้าง Unsafe Autonomous Decision แต่ยังไม่สามารถให้ผล Normal Case
ที่ชัดกว่านี้ได้เมื่อข้อมูลสำคัญหลายส่วนเป็น UNKNOWN จึงใช้ Manual Review แบบ
Conservative และให้ Claim Officer ตัดสินใจต่อ

### TC02 — Illegal Street Racing

#### Scenario

ลูกค้าชนรถขณะเข้าร่วม Illegal Street Race

#### Assignment / Expected Behavior

ตรวจพบ Illegal Racing, ใช้ Explicit Policy Exclusion, ประเมิน Not Covered และ
แนะนำ Rejection Review

#### Important Input

- Description: `Customer crashed while participating in an illegal street race`
- Submitted: Claim Form, Photos of Damage, Police Report
- Claim History: No prior claim

#### AI Semantic Extraction

Local LLM เสนอ `illegal_racing = true` ส่วน Event Type เดิมอาจยังเป็น UNKNOWN

#### Human Review / Confirmation

Claim Officer ตรวจและยืนยัน `illegal_racing = true` ก่อนใช้ Fact นี้กับ Policy Rule

#### Deterministic Evaluation

```text
Confirmed illegal_racing = true
    → Explicit Policy Exclusion: Damage from illegal racing
    → Initial Coverage Assessment: Not covered
    → Rejection review
```

LLM ไม่ได้เป็นผู้ตัดสิน Reject Claim แต่มีหน้าที่เสนอ Semantic Fact เท่านั้น

#### Actual Prototype Result

Coverage `Not covered`; Routing `Rejection review`

#### Comparison

| Check | Expected | Actual | Result |
|---|---|---|---|
| Illegal racing detection | TRUE | TRUE | PASS |
| Policy exclusion | Triggered | `Damage from illegal racing` triggered | PASS |
| Coverage | Not covered | Not covered | PASS |
| Routing | Rejection review | Rejection review | PASS |
| Human final decision | Required | Required | PASS |

#### Status

**PASS**

#### Observation / Limitation

ผลนี้แสดงการแบ่ง Responsibility ที่ชัดเจน: LLM เสนอ Fact, Human Confirm และ
Deterministic Policy Logic เป็นผู้สร้าง Recommendation

### TC03 — Vehicle Theft

#### Scenario

รถถูกขโมยจากลานจอดรถของ Condominium

#### Assignment / Expected Behavior

ตรวจ Event Type เป็น Theft, บังคับ Theft-specific Police Report Requirement และ
Route ไป Manual Review เมื่อเอกสารไม่ครบ

#### Important Input

- Description: `Vehicle stolen from condominium parking`
- Submitted: Claim Form, Vehicle Registration
- Claim History: No prior claim

#### AI Semantic Extraction

Local LLM เสนอ `event_type = theft`

#### Human Review / Confirmation

Claim Officer ตรวจและยืนยัน Theft ก่อนเข้า Document / Coverage Rules

#### Deterministic Evaluation

- Coverage: `Possibly covered`
- Theft-specific reasoning: `Police report is required`
- Missing IDs ที่พบ: `copy_of_driving_license`, `photos_of_damage`,
  `incident_report`, `police_report`
- Routing: `Manual review`

#### Actual Prototype Result

Police Report ที่ขาดถูกตรวจพบและแสดงก่อน General Missing Information จากนั้นระบบ
แนะนำ `Manual review`

#### Comparison

| Check | Expected | Actual | Result |
|---|---|---|---|
| Event type | Theft | Theft | PASS |
| Police Report requirement | Required | Required | PASS |
| Missing Police Report | Detected | Detected | PASS |
| Coverage | Not final / review required | Possibly covered | PASS |
| Routing | Manual review | Manual review | PASS |
| Human final decision | Required | Required | PASS |

#### Status

**PASS**

#### Observation / Limitation

`photos_of_damage` อาจดูไม่ตรงธรรมชาติของรถที่ถูกขโมย แต่เกิดจาก General Document
Rule ปัจจุบัน จึงบันทึกตามผลจริงและไม่ได้แก้หรือลด Policy Requirement

### TC04 — Severe Damage + Weak Evidence

#### Scenario

รถเสียหายด้านหน้าอย่างรุนแรงและมีเพียงภาพเดียวที่ไม่ชัด

#### Assignment / Expected Behavior

ตรวจ Severe Damage ร่วมกับ Weak Evidence และส่ง Fraud Review เพื่อให้ตรวจสอบเพิ่ม

#### Important Input

- Description: `Severe front-end damage with only one unclear photo`
- Submitted: One unclear photo
- Claim History: `4 claims in past 12 months`

#### AI Semantic Extraction

- `severe_damage = true`
- `weak_evidence = true`
- Explicit Assignment History สนับสนุน Advisory Fact `repeated_claims = true`
- Event Type ยังคง `unknown` เพราะข้อมูลไม่ได้ระบุ Collision, Flood, Theft หรือ
  Covered Event อื่นอย่างเพียงพอ

ข้อความ Claim History เป็น Test Evidence ไม่ใช่ Numeric Policy Threshold

#### Human Review / Confirmation

Claim Officer ตรวจและยืนยัน Risk Facts ก่อน Risk Engine ใช้งาน

#### Deterministic Evaluation

- Coverage: `Cannot determine`
- Risk Flags: `Repeated claims`; `Severe damage with weak evidence`
- Routing: `Fraud review`
- `fraud_conclusion` ยังคง false

#### Actual Prototype Result

`Fraud review`

#### Comparison

| Check | Expected | Actual | Result |
|---|---|---|---|
| Severe damage | TRUE | TRUE | PASS |
| Weak evidence | TRUE | TRUE | PASS |
| Combined risk signal | Detected | `Severe damage with weak evidence` | PASS |
| Coverage | Requires further assessment | Cannot determine | PASS |
| Routing | Fraud review | Fraud review | PASS |
| Human final decision | Required | Required | PASS |

#### Status

**PASS**

#### Observation / Limitation

Fraud Review คือ Route สำหรับการตรวจเพิ่ม ไม่ใช่ข้อสรุปว่าลูกค้าทำ Fraud
Event Type ที่เป็น UNKNOWN เป็น Safe Handling ของข้อมูลที่ไม่พอ ไม่ใช่ Hallucination

### TC05 — Late Submission

#### Scenario

Flood Claim ถูกยื่นหลัง Incident 45 วัน และ Description ระบุว่าไม่มีเหตุผลสำหรับ
Late Submission

#### Assignment / Expected Behavior

คำนวณระยะเวลาเกิน 30 วัน, เข้าใจว่าไม่มี Valid Reason และรักษา Human Review ตาม
เงื่อนไข Policy ฉบับเต็ม

#### Important Input

- Incident Date: `2026-01-01`
- Claim Submitted Date: `2026-02-15`
- Difference: `45 days`
- Description: `No reason for late submission was provided`

#### AI Semantic Extraction

- Event Type: `flood` — PASS
- Expected `late_submission_valid_reason = false`
- Observed `late_submission_valid_reason = unknown` — **LIMITATION**

Explicit Negative Statement ไม่ถูกแปลงเป็น FALSE ตามที่คาด จึงเป็น Semantic
Extraction Limitation ที่ต้องบันทึกแยกจาก Routing Result

#### Human Review / Confirmation

Claim Officer รักษาค่า UNKNOWN เมื่อ Valid Reason ยังไม่ได้รับการยืนยัน และ Confirm
ความไม่แน่นอนก่อนส่งไป Deterministic Triage

#### Deterministic Evaluation

Python คำนวณ `2026-01-01 → 2026-02-15 = 45 days` และตรวจพบว่าเกิน
More-than-30-day Condition อย่างไรก็ตาม Policy ระบุครบว่า:

> Claim filed more than 30 days after the incident without valid reason

เมื่อ Valid Reason ยังเป็น UNKNOWN ระบบจึงไม่สรุป Exclusion อัตโนมัติ แต่แสดง
Unresolved Information และ Route ไป Human Review

#### Actual Prototype Result

- Coverage: `Possibly covered`
- Routing: `Manual review`
- Final Decision: Pending Human Claim Officer Review

#### Comparison

| Check | Expected | Actual | Result |
|---|---|---|---|
| Event type | Flood | Flood | PASS |
| Submission delay | >30 days | 45 days | PASS |
| Valid late reason | FALSE | UNKNOWN | LIMITATION |
| Coverage | Review / not final | Possibly covered | PASS |
| Routing | Manual review | Manual review | PASS |
| Human final decision | Required | Required | PASS |

#### Status

**PASS WITH LIMITATION**

#### Observation / Limitation

Semantic Extraction ไม่สมบูรณ์ แต่ Deterministic Date Logic และ Conservative
Routing ทำงานถูกต้อง ข้อจำกัดนี้ไม่ถูกซ่อนและไม่ถูกเปลี่ยนเป็น Perfect PASS

## What the Assignment Tests Validate

| Test Case | Primary Capability Validated |
|---|---|
| TC01 | Conservative handling of unresolved information |
| TC02 | Policy Exclusion detection and deterministic rejection routing |
| TC03 | Event-specific required document logic |
| TC04 | Risk signal combination and Fraud Review escalation |
| TC05 | Deterministic date / late-submission handling |

เมื่อรวมกัน ทั้ง 5 Cases ทดสอบ Semantic Extraction, TRUE/FALSE/UNKNOWN Handling,
Human Confirmation, Policy Exclusion, Required Document Rules, Risk Engine,
Date Calculation, Routing Logic, Explainability และ Human Final Decision Boundary

## AI vs Deterministic Evaluation

| Responsibility | Mechanism |
|---|---|
| Understand free-text Claim | Local LLM |
| Semantic Fact Extraction | Local LLM |
| Suggest Event Type | Local LLM |
| Suggest Exclusion / Risk facts | Local LLM |
| Validate structured output | Pydantic |
| Review semantic correctness | Human Claim Officer |
| Required Document checking | Deterministic Rules |
| Date calculation | Deterministic Logic |
| Policy Exclusion evaluation | Deterministic Rules |
| Risk combination / escalation | Deterministic Risk Logic |
| Routing recommendation | Deterministic Logic |
| Final Claim Decision | Human Claim Officer |

Routing PASS ไม่ได้หมายความว่า LLM Semantic Extraction สมบูรณ์ TC05 แสดงความ
แตกต่างนี้ชัดที่สุด: Semantic Fact มี Limitation แต่ Date Calculation และ Safe
Routing ยังคงทำงานตาม Deterministic Logic

## Result Interpretation

### PASS

Critical Expected Behavior และ Actual Prototype Behavior ตรงกัน

### PASS WITH LIMITATION

Critical End-to-End Behavior ถูกต้อง แต่พบ Semantic หรือ Quality Limitation
ที่ไม่ Block Safe Result

### PARTIAL

Prototype ทำงานอย่างปลอดภัย แต่ยังไม่ตรง Intended Assignment Behavior ทั้งหมด

### FAIL

Critical Expected Behavior ไม่สำเร็จ หรือระบบให้ Unsafe / Incorrect Route

## Automated Tests vs Manual Assignment Validation

### Automated Test Suite

Canonical command:

```text
uv run pytest -q
```

Fresh verified result:

```text
118 passed
0 failed
0 warnings
```

Automated Tests ตรวจ deterministic rules, schemas, provider adapters, workflow
boundaries และ UI adapters โดยไม่ต้องใช้ Live Ollama ในทุก Test

### Manual / End-to-End Assignment Validation

TC01–TC05 ถูกตรวจผ่าน Gradio Workflow และ Real Local LLM Proposal ตามหลักฐานที่
บันทึกไว้ โดยมีผล:

- TC01 — PARTIAL
- TC02 — PASS
- TC03 — PASS
- TC04 — PASS
- TC05 — PASS WITH LIMITATION

ดังนั้น `118 passed` ไม่ได้แปลว่า Local LLM ให้ Semantic Result สมบูรณ์ 5/5 Cases

## Known Limitations

- TC01 มี Missing / Unresolved Information หลายรายการ จึง Route แบบ Conservative
- TC05 คืน `late_submission_valid_reason = unknown` แทน Expected `false`
- General Document Rules อาจแสดงรายการที่ดูไม่เฉพาะเจาะจงกับ Scenario เช่น
  `photos_of_damage` ใน Theft Case
- Confirmation-required Reasoning อาจมีรายละเอียดมากเกินไปสำหรับ Presentation UI
- Local LLM Output ยังต้องได้รับ Human Review และ Correction

## Overall Assignment Result

ทั้ง 5 Assignment Scenarios แสดงว่า Prototype รองรับ Critical Deterministic
Behavior สำหรับ Policy Exclusion, Theft-specific Document Requirement,
Risk Escalation และ Late Submission ได้

Evaluation ยังเปิดเผย Local LLM Semantic Limitation โดยเฉพาะ Explicit Negative
Statement เช่น `no reason was provided` ซึ่งยังถูกคืนเป็น UNKNOWN

ไม่มีการคำนวณหรืออ้าง Accuracy Percentage เพราะ Automated Tests และ Manual LLM
Evaluation วัดคนละ Layer และยังไม่มี Calibrated Accuracy Metric

No Assignment Test Case allows the AI to make the final Claim decision:

```text
AI Suggested Facts
    → Human Review
    → Human Confirmation
    → Deterministic Triage
    → Triage Recommendation
    → Human Final Decision
```

Human Final Decision Boundary เป็น Intentional Safety / Governance Design
ไม่ใช่ Missing Feature
