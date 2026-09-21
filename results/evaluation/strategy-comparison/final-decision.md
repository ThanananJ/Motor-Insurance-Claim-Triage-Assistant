# Phase 2.2 Final Strategy Decision

Status: **INCONCLUSIVE**

Strategy B did not demonstrate better extraction: it returned no complete
response in 0/4 targeted calls, while Strategy A returned one response in 1/4.
Because the comparison was dominated by provider timeouts, this evidence is not
sufficient to conclude whether minimal JSON improves semantic extraction under
healthy runtime conditions.

Strategy B failed Gate 1, so Gate 2 was `SKIPPED_BY_GATE`. It remains isolated
and experimental. Production default remains Strategy A (`current`). No prompt,
Policy, schema, ground truth, deterministic rule, routing rule, model, or human
confirmation requirement was changed.

Recommended next action: stabilize and bound the local Ollama request execution
environment with an explicit end-to-end deadline before repeating this same
eight-invocation comparison. Do not run the full dataset until targeted calls
produce assessable responses.
