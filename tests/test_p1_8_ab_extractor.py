from src.schemas import ClaimInput
from src.services.p1_8_ab_extractor import ABConfiguration, EVENT_POLICY, LATE_POLICY, P18ABExtractor, RISK_POLICY
from tests.p1_fakes import FakeProvider, FixedPolicyRetriever


def test_matrix_changes_only_policy_size_and_schema_detail():
    claim = ClaimInput(claim_id="AB", claim_description="Vehicle damaged")
    prompts = {
        config: P18ABExtractor(FakeProvider(), FixedPolicyRetriever("Motor Insurance Policy Rules\nFULL"), config).prompts_for(claim)
        for config in ABConfiguration
    }
    assert "Motor Insurance Policy Rules" in prompts[ABConfiguration.A]["late_reason"]
    assert "Motor Insurance Policy Rules" in prompts[ABConfiguration.B]["late_reason"]
    assert LATE_POLICY in prompts[ABConfiguration.C]["late_reason"]
    assert RISK_POLICY in prompts[ABConfiguration.D]["history_risk"]
    assert EVENT_POLICY in prompts[ABConfiguration.D]["event_exclusion"]
    assert '"properties"' in prompts[ABConfiguration.A]["history_risk"]
    assert '"properties"' not in prompts[ABConfiguration.B]["history_risk"]
    assert '"properties"' in prompts[ABConfiguration.C]["history_risk"]
    assert '"properties"' not in prompts[ABConfiguration.D]["history_risk"]


def test_all_configurations_keep_identical_untrusted_input():
    claim = ClaimInput(
        claim_id="AB", claim_description="Severe damage", customer_claim_history="Repeated claims",
        documents_submitted=["One unclear photo"],
    )
    prompts = [P18ABExtractor(FakeProvider(), FixedPolicyRetriever(), c).prompts_for(claim) for c in ABConfiguration]
    for group in ("event_exclusion", "history_risk", "late_reason"):
        contexts = [prompt[group].split("<untrusted_claim_data>")[1].split("</untrusted_claim_data>")[0] for prompt in prompts]
        assert len(set(contexts)) == 1


def test_prompts_exclude_routing_and_decision_outputs():
    claim = ClaimInput(claim_id="AB", claim_description="Vehicle damaged")
    for config in ABConfiguration:
        for prompt in P18ABExtractor(FakeProvider(), FixedPolicyRetriever(), config).prompts_for(claim).values():
            assert '"recommended_routing"' not in prompt
            assert '"approval"' not in prompt
