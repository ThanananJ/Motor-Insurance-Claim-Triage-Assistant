# Limitations and Roadmap

## MVP boundaries

The prototype is decision support for initial claim triage. It does not make
final approval or rejection decisions, authorize payments, calculate
settlements, communicate with customers automatically, or connect to live
insurance systems.

The MVP uses synthetic claim data and the supplied Policy rules. It is not a
production fraud model and does not perform OCR, parse uploaded files, or
verify document/image authenticity.

## Roadmap

Completed in the prototype: validated contracts, deterministic rules, grounded
LLM proposals, basic summary/explanation, the Gradio human-review workflow, and
Assignment Case evaluation.

Deferred beyond the prototype: stronger-model evaluation, document
intelligence, fraud analytics, integrations, monitoring, access control, audit
capabilities, and enterprise deployment.

## Local model evaluation limitation

As of P1.9, no local model is accepted for MVP semantic extraction.
`qwen3:4b` improved the fixed tests and passed Case 4, but unsupported facts
changed Assignment Case 1 to Fraud review and Case 5 to Rejection review. It
must not be treated as an autonomous source of routing facts.

For the deadline-oriented prototype, the safe fallback is to preserve UNKNOWN
and send uncertain AI extraction to human review. Do not repair model semantics
with keywords, regexes, invented thresholds, or Policy changes.

P2 therefore treats every model value as an advisory proposal. Mandatory human
confirmation/correction is the trust boundary before P0, and the Claim Officer
still owns the final claim decision after receiving the routing recommendation.
Further local-model evaluation is deferred until after the deadline prototype.
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
Future work may evaluate a stronger model, add OCR and document/image
authenticity analysis, add production RAG for large policy collections,
persist claims, introduce authentication/RBAC and monitoring, and prepare an
enterprise deployment.
