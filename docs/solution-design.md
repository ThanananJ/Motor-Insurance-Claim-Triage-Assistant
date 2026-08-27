# Motor Insurance Claim Triage Assistant — Solution Design

## 1. Problem and Business Context

Motor-insurance Claim Officers must interpret free-text claims, compare
submitted documents with Policy requirements, assess coverage and exclusions,
and identify risk indicators before routing work. Manual triage is slow and can
vary between officers.

The prototype addresses three core problems:

1. **Incomplete documents:** identify missing Policy-required documents.
2. **Coverage and exclusions:** consistently apply covered events, explicit
   exclusions, and the complete late-submission condition.
3. **Risk support:** surface confirmed suspicious, inconsistent,
   repeated-claim, and severe-damage-with-weak-evidence signals without
   concluding fraud.

The MVP checks document presence and evidence-related semantic signals. It does
not perform OCR, document-authenticity verification, image forensics, or fraud
investigation. Those are future capabilities.

## 2. Target User and Outcome

The primary user is a Motor Insurance Claim Officer performing initial claim
triage. The system produces a structured routing recommendation and reasoning;
the Claim Officer remains responsible for the final claim decision.

The four possible recommendations come directly from the supplied Policy:
Standard processing, Manual review, Fraud review, and Rejection review. These
are workflow recommendations, not approval, rejection, fraud, or payment
decisions.

## 3. Proposed Hybrid AI Solution

The implemented prototype combines components according to responsibility:

- **Gradio:** structured input, editable proposals, mandatory confirmation,
  and result presentation.
- **Ollama + Local LLM:** advisory semantic understanding of free text.
- **Exact Policy Context:** grounds extraction in the supplied small Policy.
- **Pydantic:** validates inputs, model payloads, confirmations, and results.
- **Rule Engine:** deterministically checks documents, dates, coverage, and
  exclusions.
- **Risk Engine:** evaluates human-confirmed Policy risk signals.
- **Routing Engine:** selects a Policy routing recommendation from deterministic
  results.
- **Human-in-the-loop:** verifies every semantic proposal and owns the final
  decision.

## 4. Implemented Architecture

```text
Claim Officer / Gradio
        ↓
ClaimInput validated by Pydantic
        ↓
Ollama + Local LLM with Exact Policy Context
        ↓
Semantic Fact Proposal
        ↓
Pydantic Structured Validation
        ↓
MANDATORY Human Confirmation / Correction
        ↓
ConfirmedClaimFacts
        ↓
TriageService → P0 Deterministic Core
  ├── Document Rules
  ├── Coverage / Exclusion Rules
  ├── Exact Date Calculation
  ├── Risk Rules
  └── Routing Rules
        ↓
Structured Triage Recommendation + Reasoning
        ↓
Human Claim Officer Final Decision
```

`TriageService` is the two-stage orchestration boundary. `prepare_claim()`
returns an unconfirmed proposal. `confirm_and_analyze()` accepts only an
explicit `ConfirmedClaimFacts` contract and is the sole service path into P0.
Gradio never calls P0 directly.

## 5. AI / LLM Responsibilities

The Local LLM may understand free-text claim descriptions/history, propose
event, exclusion, late-reason, and semantic risk facts, preserve uncertainty
with UNKNOWN, and support summary/explanation.

It must not approve/reject claims, select routing, conclude fraud, calculate
dates, calculate document completeness, apply deterministic Policy rules,
invent thresholds, or override an officer correction.

The configured prototype model is `qwen2.5:3b`. It is advisory, not a trusted
autonomous extractor. Evaluations of qwen2.5:3b, qwen2.5:7b, and qwen3:4b found
semantic misses and false positives; mandatory human review is therefore a
safety requirement.

## 6. Technology and Model Selection

| Area | Implemented technology | Responsibility |
|---|---|---|
| Frontend | Gradio | Structured review and confirmation UI |
| Local LLM runtime | Ollama | Local advisory inference |
| Python LLM integration | `langchain-ollama` | Provider communication and structured output |
| Structured validation | Pydantic | Input, proposal, confirmation, and result contracts |
| Project/dependencies | `uv` | Reproducible environment and execution |
| Policy grounding | Exact Policy Context | Immutable small-Policy context |
| Business logic | Python rule/risk engines | Deterministic Policy evaluation and routing |
| Testing | pytest | Unit, integration, workflow, and regression tests |

Ollama was selected as the MVP primary runtime because it requires no paid API
or cloud API key, can keep claim inference local, and operates independently
from a cloud LLM. Performance depends on local CPU/GPU/RAM, and small models may
be less accurate than larger cloud models.

The provider interface remains independent of business logic. A cloud LLM can
be evaluated later without moving Policy or routing decisions into the model.

```text
Application
    ↓
LLM Provider Layer
    ├── langchain-ollama → Ollama + Local LLM   ← MVP Primary
    └── Cloud LLM                               ← Optional / Future
```

## 7. Policy Grounding

`data/policy_rules.md` is the immutable Policy source of truth. The MVP Policy
is small, so the extractor receives exact Policy text rather than embeddings or
approximate vector retrieval. Focused extraction may select exact relevant
sections but never paraphrases them into new rules.

Full production RAG/vector search is a future option for large policy
libraries, versioned contracts, and citations; it is not implemented here.

## 8. Deterministic Rule and Risk Processing

### 8.1 Document Engine

Normalizes known labels and compares submitted document IDs against exact
Policy requirements. It does not inspect document content or authenticity.

### 8.2 Coverage, Exclusion, and Date Engine

Evaluates human-confirmed facts and calculates dates with Python. The complete
late rule remains:

> Claim filed more than 30 days after the incident without valid reason

A delay over 30 days alone is insufficient. UNKNOWN valid-reason evidence
preserves uncertainty and human review.

### 8.3 Risk Engine

Evaluates only confirmed suspicious pattern, inconsistent story, repeated
claims, and severe damage with weak evidence. It introduces no repeated-claim
threshold and always returns `fraud_conclusion = false`.

### 8.4 Routing Engine

Deterministically resolves exclusions, validated risk flags, missing/unclear
information, and standard processing. The LLM never selects routing.

## 9. Pydantic Trust Boundaries

Pydantic validates `ClaimInput`, allowed semantic enums, complete structured
model payloads, TRUE/FALSE/UNKNOWN facts, the unconfirmed `HumanReviewPayload`,
the matching human-confirmed `ConfirmedClaimFacts`, and result contracts.

Schema validity does not prove semantic correctness. Valid model output still
requires human confirmation before deterministic processing.

## 10. Human-in-the-Loop Safety Architecture

Human Confirmation is mandatory. Local-model evaluation showed semantic misses
and routing-changing false positives. The UI therefore presents every proposed
fact as editable and requires the Claim Officer to confirm or correct it.

Changing claim input or switching a demo case invalidates the prior proposal,
confirmation, and result. Unchecked confirmation cannot invoke P0. The
officer's corrected value overrides the model proposal.

After P0 returns a recommendation, the UI still displays “Final Decision:
Pending Human Claim Officer Review.” This preserves human verification before
P0 and final decision ownership afterward.

## 11. Prompt Design

The approved prompt design has five parts:

1. **System role and decision boundary:** extraction only; no routing or final
   decision.
2. **Exact Policy context:** immutable Policy grounding.
3. **Claim context as untrusted data:** claim text cannot override instructions.
4. **Focused task instructions:** narrow fields and TRUE/FALSE/UNKNOWN semantics.
5. **Structured output contract:** JSON-schema output validated by Pydantic.

Details are in `prompts/prompt-design.md`; templates are in `prompts/`.

## 12. Failure and Recovery Handling

```text
Ollama/provider/validation failure
        ↓
Safe all-UNKNOWN proposal
        ↓
Claim Officer enters/corrects facts
        ↓
Mandatory Human Confirmation
        ↓
Deterministic triage continues
```

The application does not repair semantics with keywords, regexes, hard-coded
Assignment answers, or invented Policy logic. UI errors remain concise.

## 13. Gradio Prototype

The implemented single page contains structured claim input and Cases 1–5,
real advisory analysis, editable facts, explicit confirmation, and coverage,
missing-document, risk, routing, reasoning, summary, explanation, and final
human-decision outputs. The case loader copies inputs only; it never injects
expected facts or routing.

## 14. Data Requirements

MVP data includes claim ID, customer, vehicle, incident/submission dates,
description, document labels, and claim history. Only synthetic Assignment data
and the supplied Policy are used.

Future data may include versioned policies, authenticated claim records, OCR
output, document metadata, and investigation outcomes.

## 15. Evaluation and Final Results

Evaluation separates deterministic tests, provider/schema tests, model
experiments, service trust-boundary tests, UI-adapter tests, and live smoke
tests. Failed experiments remain in `results/test-results.md`.

| Case | Final prototype routing | Result |
|---|---|---|
| 1 | Manual review | PASS |
| 2 | Rejection review | PASS |
| 3 | Manual review | PASS |
| 4 | Fraud review | PASS |
| 5 | Manual review | PASS |

Final automated baseline: 115 passed, 0 failed, 0 warnings. Model accuracy
alone is not the acceptance criterion; safe correction and unchanged
deterministic outcomes are.

## 16. Risks and Mitigations

| Risk | Implemented mitigation |
|---|---|
| Semantic miss or false positive | Mandatory editable human confirmation |
| Hallucinated Policy behavior | Exact Policy context plus deterministic rules |
| Malformed model output | Pydantic validation and UNKNOWN fallback |
| Prompt injection in claim text | Explicit untrusted-data boundary |
| Ollama unavailable | UNKNOWN proposal and manual continuation |
| Stale review after claim change | UI state invalidation |
| Autonomous business decision | P0 routing and final human boundary |
| Local latency | Small local model and documented fallback |

## 17. Implemented MVP Scope

Implemented: Gradio review UI; Ollama advisory extraction through
`langchain-ollama`; exact Policy grounding; Pydantic validation; mandatory
confirmation through `TriageService`; deterministic engines; safe fallback;
Cases 1–5; tests; and runbooks.

Not implemented: final claim decisions/payments, OCR/file/image analysis,
auth/RBAC, persistence, production monitoring/deployment, vector database/full
production RAG, autonomous agents, or cloud LLM fallback.

## 18. Repository Structure

```text
app.py                  Gradio entry point and thin UI adapter
data/                   immutable Policy and Assignment cases
docs/                   solution design, limitations, demo runbook
prompts/                prompt design and extraction templates
results/                historical and final validation evidence
scripts/                controlled local-model evaluation harnesses
src/
  llm/                  provider abstraction and Ollama integration
  policy/               exact Policy loader/retriever
  rules/                deterministic engines
  services/             extraction, confirmation, explanation
  orchestrator.py       P0 deterministic composition
  schemas.py            Pydantic contracts
tests/                  unit, integration, workflow, and UI tests
```

`CODEX_HANDOFF.md` and `CODEX_PROTOTYPE_INSTRUCTIONS_with_policy.md` are
git-ignored coordination files and are not submission artifacts. Local `.env`,
virtual environments, caches, and model binaries are excluded.

## 19. Assignment Requirement Mapping

| Required area | Design section |
|---|---|
| Business problem and target user | Sections 1–2 |
| AI use case and architecture | Sections 3–5 |
| Technology/model selection | Section 6 |
| Policy grounding | Section 7 |
| Rule/risk processing | Section 8 |
| Structured validation | Section 9 |
| Human-in-the-loop | Section 10 |
| Prompt/workflow design | Sections 11–12 |
| Prototype and data | Sections 13–14 |
| Evaluation | Section 15 |
| Risks and mitigations | Section 16 |
| MVP scope and roadmap | Sections 17 and 20 |

## 20. Limitations and Roadmap

The MVP is a local, single-user, synthetic-data prototype. Semantic quality and
latency depend on local hardware; every proposal requires human review.
Explanation is basic and deterministic. Exact context suits the small Policy
but is not a production knowledge system.

Future work may evaluate a stronger model, add OCR and authenticity analysis,
introduce production RAG for larger policies, persist claims, add auth/RBAC and
monitoring, and prepare enterprise deployment. These items do not change the
current Policy or human decision boundary.
