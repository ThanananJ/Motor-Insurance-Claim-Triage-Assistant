"""Controlled prototype routing precedence.

The precedence here is implementation workflow behavior, not additional Policy
wording. Values remain limited to the four routes supplied by the Policy.
"""

from src.schemas import CoverageAssessment, CoverageEvaluation, DocumentCheckResult, RiskEvaluation, Routing


def resolve_routing(
    document_check: DocumentCheckResult,
    coverage: CoverageEvaluation,
    risk: RiskEvaluation,
) -> Routing:
    if coverage.triggered_exclusions:
        return Routing.REJECTION_REVIEW
    if risk.risk_flags:
        return Routing.FRAUD_REVIEW
    if (
        document_check.missing_document_ids
        or coverage.unresolved_information
        or coverage.assessment is not CoverageAssessment.LIKELY_COVERED
    ):
        return Routing.MANUAL_REVIEW
    return Routing.STANDARD_PROCESSING
