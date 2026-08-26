"""P0 deterministic claim-analysis workflow."""

from src.rules.coverage_rules import evaluate_coverage
from src.rules.document_rules import evaluate_documents
from src.rules.risk_rules import evaluate_risk
from src.rules.routing_rules import resolve_routing
from src.schemas import ClaimFacts, ClaimInput, DeterministicAnalysisResult, Routing


def analyze_claim(claim: ClaimInput, facts: ClaimFacts) -> DeterministicAnalysisResult:
    document_check = evaluate_documents(claim, facts.event_type)
    coverage = evaluate_coverage(claim, facts)
    risk = evaluate_risk(facts)
    routing = resolve_routing(document_check, coverage, risk)

    missing_information = list(document_check.missing_information)
    for item in coverage.unresolved_information:
        if item not in missing_information:
            missing_information.append(item)

    reasoning_points: list[str] = []
    if coverage.triggered_exclusions:
        reasoning_points.append(
            "Explicit Policy exclusion confirmed: " + "; ".join(coverage.triggered_exclusions)
        )
    if risk.risk_flags:
        reasoning_points.append(
            "Validated risk signal(s) require review: " + "; ".join(risk.risk_flags)
        )
    if missing_information:
        reasoning_points.append("Missing or unresolved information: " + "; ".join(missing_information))
    if routing is Routing.STANDARD_PROCESSING:
        reasoning_points.append("Covered event is clear, required documents are complete, and no risk flags are present")
    reasoning_points.append("This is a routing recommendation; the Claim Officer makes the final decision")

    return DeterministicAnalysisResult(
        document_check=document_check,
        coverage=coverage,
        risk=risk,
        recommended_routing=routing,
        missing_information=missing_information,
        reasoning_points=reasoning_points,
    )
