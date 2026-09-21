# Evaluation Summary

Static policy grounding is used; Retrieval Evaluation is not applicable in the current implementation.

| Level | Mode | Status | Passed | Total |
|---|---|---:|---:|---:|
| model | live | SKIPPED | 0 | 9 |

## Quality gates

### Model
- FAIL — `json_parse_at_least_95_percent`
- FAIL — `schema_valid_at_least_95_percent`
- FAIL — `field_f1_at_least_0_85`
- FAIL — `critical_exclusion_recall_100_percent`
- FAIL — `critical_risk_recall_100_percent`
- PASS — `unsupported_critical_facts_zero`
- PASS — `llm_final_decisions_zero`
- FAIL — `live_cases_assessed`
