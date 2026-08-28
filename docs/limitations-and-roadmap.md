# Limitations and Roadmap

## MVP boundaries

The prototype is decision support for initial claim triage. It does not make
final approval or rejection decisions, authorize payments, calculate
settlements, communicate with customers automatically, or connect to live
insurance systems.

The MVP uses synthetic claim data and the supplied Policy rules. It is not a
production fraud model and does not perform OCR, parse uploaded files, or
verify document/image authenticity.

## Final MVP status

Completed in the prototype: validated contracts, deterministic rules, grounded
LLM proposals, basic summary/explanation, the Gradio human-review workflow, and
Assignment Case evaluation.

The final MVP workflow is:

```text
Local LLM / Ollama
    → Semantic Extraction
    → AI Suggested Facts
    → Pydantic Validation
    → Human Review / Correction
    → Explicit Human Confirmation
    → Deterministic Triage
    → Triage Recommendation
    → Human Final Decision
```

The Local LLM is active in the prototype, but its output is advisory and
untrusted. Pydantic validates structure and allowed values; the Claim Officer
validates semantic correctness. Unconfirmed AI output cannot drive routing.

## Local model status and evaluation findings

The final MVP uses Ollama with `qwen2.5:3b` to generate AI Suggested Facts.
This is an accepted **advisory prototype path**, not an acceptance of the model
as an autonomous source of Policy facts, routing, or Claim decisions.

Earlier P1.5–P1.9 evaluations remain useful findings: `qwen2.5:3b`,
`qwen2.5:7b`, and `qwen3:4b` produced semantic misses and false positives.
For example, `qwen3:4b` improved some fixed cases but unsupported facts changed
Case 1 to Fraud review and Case 5 to Rejection review. The final Assignment
validation also observed `late_submission_valid_reason = unknown` instead of
`false` for an explicit “no reason was provided” statement.

For the deadline-oriented prototype, the safe fallback is to preserve UNKNOWN
and send uncertain AI extraction to human review. Two narrow Assignment-fixture
interpretations surface explicit third-party wording and the exact history
phrase “4 claims in past 12 months” as advisory facts. They are presentation
scaffolding—not general insurance rules, calibrated inference, or a numeric
repeated-claims Policy threshold—and still require human confirmation.

The final workflow therefore treats every model value as an advisory proposal.
Mandatory human confirmation/correction is the trust boundary before
deterministic triage, and the Claim Officer still owns the final claim decision
after receiving the routing recommendation.

The current explanation is deliberately basic deterministic text; richer LLM
wording is optional future work and cannot modify analysis fields.

The Gradio interface is a local, single-user presentation prototype. It has no
authentication, RBAC, persistence, concurrency guarantees, production
monitoring, cloud deployment, or production security hardening. Dates use
validated `YYYY-MM-DD` text fields. Local inference speed depends on CPU/GPU/RAM
and P4 observed roughly 8–18 seconds per Assignment proposal. The demo-case
loader copies input evidence only; the officer must still review and confirm
facts before P0.

The MVP uses exact context grounding because the supplied Policy is small. It
does not implement embeddings, a vector database, or production-scale RAG.

## Roadmap by product outcome

### Near-term — AI Quality & Evaluation

The first priority is to understand and reduce recurring semantic errors while
keeping the current Human-in-the-Loop boundary:

- evaluate stronger Local and optional Cloud LLMs through the same provider boundary;
- expand Semantic Extraction evaluation beyond the five Assignment cases;
- improve TRUE / FALSE / UNKNOWN handling, especially explicit negative statements;
- improve explanation quality without allowing generated text to change routing;
- build a controlled Human Feedback / Evaluation Dataset.

Human corrections can support an evidence loop:

```text
AI Suggested Facts
    → Claim Officer Correction
    → Store reviewed corrections
    → Controlled Evaluation Dataset
    → Measure recurring model errors
    → Improve prompts / models / evaluation
```

Corrections must not automatically retrain a model, change a prompt, or modify
production behavior. Dataset creation, review, privacy controls, and any model
change require a governed process.

### Mid-term — Claim Officer Experience

#### Chatbot + Structured Claim Workspace

The original UX concept can evolve into a Conversational Chatbot combined with
a Structured Claim Panel. A Claim Officer could provide information using
Natural Language while the workspace updates reviewable fields such as Event
Type, Documents, Exclusion-related Facts, Risk Signals, and Missing Information.

Chatbot is an interface enhancement, not a decision-maker. AI Suggested Facts
must remain visible and editable, and the Officer must still Review, Correct,
and Confirm them before deterministic triage.

#### OCR / Document Intelligence

A future document workflow could be:

```text
Uploaded Claim Documents
    → OCR / Document Parsing
    → Extract Document Facts
    → Structured Validation
    → Human Review
```

Possible inputs include Claim Forms, Police Reports, Driving Licences, and
Damage Photos. Document/image authenticity analysis may be evaluated later;
neither OCR nor authenticity detection is implemented in the current MVP.

#### Production Policy RAG

Exact Policy Grounding remains appropriate for the small, fixed Assignment
Policy. When the knowledge base expands across products, Policy versions,
endorsements, and larger documents, the solution can introduce retrieval:

```text
Claim Context
    → Retrieve Relevant Policy
    → Policy Section / Version
    → LLM / Deterministic Rules
    → Recommendation
```

Policy Citation / Reference should show the Claim Officer which section and
version supports the Recommendation. This improves Explainability,
Traceability, and Officer trust. The current MVP does not use Vector RAG.

### Long-term — Production Integration & Governance

Production readiness requires coordinated business, security, data, and
operational work:

- Insurance Core System integration;
- Authentication and Role-Based Access Control (RBAC);
- Persistent Claim State and concurrency-safe workflows;
- Audit Trail for Model, Prompt, Rule, confirmed facts, and output versions;
- Monitoring, Observability, alerting, and operational fallback;
- Privacy, retention, access, and security hardening;
- Enterprise deployment and support processes.

Auditability should make this trace possible:

```text
Claim Input
    → AI Suggested Facts
    → Human Corrections
    → Confirmed Facts
    → Model / Prompt / Rule Version
    → Recommendation / Output
```

These controls are future production capabilities and must not be interpreted
as implemented MVP features.

## Roadmap summary

```text
MVP
    ↓
AI Quality & Evaluation
    ↓
Chatbot + Structured Workspace
    ↓
Document Intelligence
    ↓
Production Policy RAG
    ↓
Core Insurance Integration
    ↓
Monitoring / Audit / Enterprise Deployment
```

This is a conceptual product roadmap, not a fixed delivery schedule. AI
quality, UX, document, Policy, and governance tracks may evolve in parallel.

## Proposed Product Direction

The intended direction is to reduce the cognitive and manual workload of the
Claim Officer without replacing decision authority:

1. Keep Human-in-the-Loop as a permanent design principle.
2. Make review easier through Chatbot + Structured Claim Workspace.
3. Reduce manual document handling through Document Intelligence.
4. Scale Exact Policy Grounding into Production Policy RAG as Policy volume grows.
5. Use Human corrections as controlled evaluation feedback—not automatic learning.
6. Move toward deeper production integration only after quality, workflow, and
   governance controls are demonstrated.

AI should help the Claim Officer collect, organize, and review evidence more
consistently. The Human Claim Officer remains responsible for the final Claim
decision.
