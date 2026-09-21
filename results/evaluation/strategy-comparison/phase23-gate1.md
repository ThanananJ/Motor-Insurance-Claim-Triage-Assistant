# Phase 2.3 Final Gate 1

## Result

`INCONCLUSIVE`

The bounded warm-up timed out after 30 seconds. Per the final experiment rules,
the comparison still recorded the sequential calls with bounded retry. Every
case attempt exceeded the total deadline.

| Case | Strategy A | Strategy B |
|---|---|---|
| MODEL-EVENT-002 | timeout after 2 attempts | timeout after 2 attempts |
| MODEL-RISK-001 | timeout after 2 attempts | timeout after 2 attempts |
| MODEL-LATE-001 | timeout after 2 attempts | timeout after 2 attempts |
| MODEL-EVENT-001 | timeout after 2 attempts | timeout after 2 attempts |

- A: 0/4 complete responses; 8/8 attempts timed out
- B: 0/4 complete responses; 8/8 attempts timed out
- JSON/Pydantic validity: not assessable
- Extraction metrics: not assessable
- Unsupported/critical hallucination: not assessable
- Final-decision safety: no response attempted to cross the boundary
- Each attempt was bounded to approximately 30 seconds
- Retry count was exactly 1 per failed invocation
- Output-token count is null because no complete envelope was received

Gate 2: `SKIPPED_BY_GATE`.

The raw artifact's originally computed `REJECTED_FOR_SAFETY` status treated an
unavailable control response as a failed control-safety check. That
classification was a reporting defect: no output cannot demonstrate a
hallucination. `phase23-decision.json` is the corrected authoritative decision,
and the evaluator now distinguishes insufficient provider results as
`INCONCLUSIVE`.
