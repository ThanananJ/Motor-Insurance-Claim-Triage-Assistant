# Evaluation Summary

Static policy grounding is used; Retrieval Evaluation is not applicable in the current implementation.

| Level | Mode | Status | Passed | Total |
|---|---|---:|---:|---:|
| model | fixture | PASS | 9 | 9 |
| component | fixture | PASS | 10 | 10 |
| e2e | fixture | PASS | 10 | 10 |

## Quality gates

### Model
- PASS — `json_parse_at_least_95_percent`
- PASS — `schema_valid_at_least_95_percent`
- PASS — `field_f1_at_least_0_85`
- PASS — `critical_exclusion_recall_100_percent`
- PASS — `critical_risk_recall_100_percent`
- PASS — `unsupported_critical_facts_zero`
- PASS — `llm_final_decisions_zero`
- PASS — `live_cases_assessed`

### Component
- PASS — `all_components_pass`
- PASS — `safety_critical_100_percent`
- PASS — `retrieval_evaluation_not_fabricated`

### E2E
- PASS — `exact_routing_at_least_80_percent`
- PASS — `safe_fallback_100_percent`
- PASS — `human_boundary_100_percent`
- PASS — `critical_safety_failures_zero`
- PASS — `ai_final_decisions_zero`
