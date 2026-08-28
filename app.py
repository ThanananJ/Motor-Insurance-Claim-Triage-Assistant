"""Gradio entry point for the human-confirmed claim-triage prototype."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import gradio as gr
from langchain_ollama import ChatOllama

from src.config import AppConfig
from src.llm.ollama_provider import OllamaProvider
from src.policy.retriever import ExactPolicyRetriever
from src.schemas import ClaimFacts, ClaimInput, ConfirmedClaimFacts, EventType, FactStatus
from src.services.p1_8_ab_extractor import ABConfiguration, P18ABExtractor
from src.services.triage_service import TriageService


ROOT = Path(__file__).parent
FACT_FIELDS = tuple(ClaimFacts.model_fields)
EVENT_CHOICES = [item.value for item in EventType]
STATUS_CHOICES = [FactStatus.UNKNOWN.value, FactStatus.TRUE.value, FactStatus.FALSE.value]
DOCUMENT_CHOICES = [
    "Claim form", "Copy of driving license", "Vehicle registration",
    "Photos of damage", "Incident report", "Police report",
    "Third-party contact information and evidence", "One unclear photo",
]
DEMO_CASES = {
    item["case_id"]: item
    for item in json.loads((ROOT / "data" / "test_cases.json").read_text(encoding="utf-8"))
}


def load_local_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_local_env()


class RuntimeSemanticExtractor:
    """Build the configured advisory Ollama extractor only when requested."""

    def extract(self, claim: ClaimInput):
        config = AppConfig.from_env()
        if config.ollama_model and config.ollama_model.casefold().startswith("qwen3"):
            provider = OllamaProvider(
                config,
                chat_model_factory=lambda **kwargs: ChatOllama(**kwargs, reasoning=False),
            )
        else:
            provider = OllamaProvider(config)
        return P18ABExtractor(provider, ExactPolicyRetriever(), ABConfiguration.C).extract(claim)


TRIAGE_SERVICE = TriageService(RuntimeSemanticExtractor())


def optional_date(value: str | None) -> date | None:
    value = (value or "").strip()
    return date.fromisoformat(value) if value else None


def build_claim_input(claim_id, customer, vehicle, description, history, incident_date, submitted_date, documents):
    return ClaimInput(
        claim_id=claim_id.strip(), customer=customer.strip() or None,
        vehicle=vehicle.strip() or None, claim_description=description.strip(),
        customer_claim_history=history.strip() or None,
        incident_date=optional_date(incident_date),
        claim_submitted_date=optional_date(submitted_date),
        documents_submitted=documents or [],
    )


def load_demo_case(selection: str):
    if selection == "Custom Claim":
        return "", "", "", "", "", "", "", []
    case_id = int(selection.rsplit(" ", 1)[1])
    item = DEMO_CASES[case_id]
    return (
        f"DEMO-{case_id}", f"Demo Customer {case_id}", f"Demo Vehicle {case_id}",
        item["scenario"], item["claim_history"] or "",
        "2026-01-01" if case_id == 5 else "",
        "2026-02-15" if case_id == 5 else "", item["documents_submitted"],
    )


def reset_review_ui():
    """Invalidate advisory and result state whenever claim inputs change."""

    empty_result = ("", "No result yet.", "No result yet.", "", "No result yet.", "No result yet.", "", "")
    final_notice = (
        "**Final Decision: Pending Human Claim Officer Review.** "
        "This is an AI-assisted triage recommendation, not a final claim decision."
    )
    return (
        None,
        "Claim input changed. Analyze this claim before confirmation.",
        *[EventType.UNKNOWN.value, *([FactStatus.UNKNOWN.value] * (len(FACT_FIELDS) - 1))],
        False,
        *empty_result,
        final_notice,
    )


def clear_result_ui():
    """Clear a previous deterministic result before a new AI analysis."""

    return (
        "", "No result yet.", "No result yet.", "", "No result yet.", "No result yet.", "", "",
        "**Final Decision: Pending Human Claim Officer Review.** "
        "This is an AI-assisted triage recommendation, not a final claim decision.",
    )


def prepare_with_service(service: TriageService, *values):
    review = service.prepare_claim(build_claim_input(*values))
    facts = review.proposal.facts
    status = (
        f"AI proposal ready — provider: {review.proposal.provider or 'unknown'}, "
        f"model: {review.proposal.model or 'unknown'}. Review every value before confirming."
        if review.proposal.extraction_success
        else "AI extraction unavailable. Safe UNKNOWN suggestions were loaded; please review, enter, and confirm facts manually."
    )
    return (review, status, *[getattr(facts, field).value for field in FACT_FIELDS], False)


def analyze_claim_ui(*values):
    try:
        return prepare_with_service(TRIAGE_SERVICE, *values)
    except Exception:
        raise gr.Error("Please check required claim fields and use YYYY-MM-DD dates.") from None


def confirm_with_service(service: TriageService, review, confirmation_checked: bool, *fact_values: str):
    blank = ("", "", "", "", "", "", "", "")
    if not confirmation_checked:
        return (*blank, "Please review and confirm/correct the AI suggested facts before running triage.")
    if review is None:
        return (*blank, "Analyze the claim first, then review and confirm the facts.")
    facts = ClaimFacts.model_validate(dict(zip(FACT_FIELDS, fact_values, strict=True)))
    result = service.confirm_and_analyze(
        review,
        ConfirmedClaimFacts(claim_id=review.claim.claim_id, facts=facts, confirmed_by_human=True),
    )
    missing = "\n".join(f"- {item}" for item in result.missing_information) or "No missing or unresolved information"
    risks = "\n".join(f"- {item}" for item in result.risk_flags) or "No validated risk signals"
    reasoning = "\n".join(f"- {item}" for item in result.deterministic_reasoning_points)
    return (
        result.initial_coverage_assessment.value, missing, risks,
        result.recommended_routing.value, result.confidence_level.value,
        reasoning, result.claim_summary,
        result.explanation,
        "Final Decision: Pending Human Claim Officer Review. " + result.recommendation_disclaimer,
    )


def confirm_claim_ui(*values):
    try:
        return confirm_with_service(TRIAGE_SERVICE, *values)
    except Exception:
        return ("", "", "", "", "", "", "", "", "Unable to run triage. Re-analyze this claim, review the facts, and try again.")


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Motor Insurance Claim Triage Assistant") as demo:
        gr.Markdown("# Motor Insurance Claim Triage Assistant")
        gr.Markdown("**Human-in-the-Loop Prototype:** The Local LLM proposes facts only. A Claim Officer must review and confirm/correct them before deterministic triage.")
        review_state = gr.State()
        gr.Markdown("## Step 1 — Claim Information")
        demo_case = gr.Dropdown(["Custom Claim", *[f"Assignment Case {i}" for i in range(1, 6)]], value="Custom Claim", label="Demo Case")
        with gr.Row():
            claim_id = gr.Textbox(label="Claim ID")
            customer = gr.Textbox(label="Customer")
            vehicle = gr.Textbox(label="Vehicle")
        description = gr.Textbox(label="Claim Description", lines=3)
        history = gr.Textbox(label="Customer Claim History", lines=2)
        with gr.Row():
            incident = gr.Textbox(label="Incident Date (YYYY-MM-DD)")
            submitted = gr.Textbox(label="Claim Submitted Date (YYYY-MM-DD)")
        documents = gr.CheckboxGroup(DOCUMENT_CHOICES, label="Submitted Documents")
        analyze_button = gr.Button("Analyze Claim with AI", variant="primary")

        gr.Markdown("## Step 2 — AI Suggested Facts — Review Required")
        gr.Markdown("The Local LLM proposes semantic facts. Suggestions are not trusted until reviewed and confirmed by the Claim Officer.")
        proposal_status = gr.Markdown("No analysis prepared.")
        event_type = gr.Dropdown(EVENT_CHOICES, value="unknown", label="Event Type")
        labels = {
            "alcohol_or_drug_involvement": "Alcohol / drug involvement", "illegal_racing": "Illegal racing",
            "intentional_damage": "Intentional damage", "outside_permitted_geographic_coverage": "Outside permitted geographic coverage",
            "late_submission_valid_reason": "Late submission valid reason", "suspicious_pattern": "Suspicious pattern",
            "inconsistent_story": "Inconsistent story", "repeated_claims": "Repeated claims",
            "severe_damage": "Severe damage", "weak_evidence": "Weak evidence",
        }
        fact_components = []
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Exclusions / Late Reason")
                for field in FACT_FIELDS[1:6]:
                    fact_components.append(gr.Dropdown(STATUS_CHOICES, value="unknown", label=labels[field]))
            with gr.Column():
                gr.Markdown("### Risk / Semantic Signals")
                for field in FACT_FIELDS[6:]:
                    fact_components.append(gr.Dropdown(STATUS_CHOICES, value="unknown", label=labels[field]))
        confirmation = gr.Checkbox(label="I have reviewed and confirmed/corrected the AI suggested facts.")
        confirm_button = gr.Button("Confirm Facts & Run Triage", variant="primary")

        gr.Markdown("## Step 3 — Triage Recommendation")
        with gr.Row():
            coverage = gr.Textbox(label="Initial Coverage Assessment", interactive=False)
            routing = gr.Textbox(label="Recommended Routing", interactive=False)
            confidence = gr.Textbox(label="Prototype Confidence Level", interactive=False)
        gr.Markdown("### Missing Information")
        missing = gr.Markdown("No result yet.")
        gr.Markdown("### Risk Signals")
        risks = gr.Markdown("No result yet.")
        gr.Markdown("### Deterministic Reasoning")
        reasoning = gr.Markdown("No result yet.")
        summary = gr.Textbox(label="Claim Summary", interactive=False)
        explanation = gr.Textbox(label="Explanation", lines=4, interactive=False)
        final_notice = gr.Markdown("**Final Decision: Pending Human Claim Officer Review.** This is an AI-assisted triage recommendation, not a final claim decision.")

        claim_components = [claim_id, customer, vehicle, description, history, incident, submitted, documents]
        review_outputs = [
            review_state, proposal_status, event_type, *fact_components, confirmation,
            coverage, missing, risks, routing, confidence, reasoning, summary, explanation, final_notice,
        ]
        demo_case.change(load_demo_case, demo_case, claim_components).then(
            reset_review_ui, outputs=review_outputs,
        )
        for component in claim_components:
            component.input(reset_review_ui, outputs=review_outputs)
        analyze_button.click(
            clear_result_ui,
            outputs=[coverage, missing, risks, routing, confidence, reasoning, summary, explanation, final_notice],
        ).then(
            analyze_claim_ui,
            claim_components,
            [review_state, proposal_status, event_type, *fact_components, confirmation],
        )
        confirm_button.click(confirm_claim_ui, [review_state, confirmation, event_type, *fact_components], [coverage, missing, risks, routing, confidence, reasoning, summary, explanation, final_notice])
    return demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch()
