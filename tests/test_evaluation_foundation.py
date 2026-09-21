from evaluation.evaluators.component_evaluator import evaluate_components
from evaluation.evaluators.e2e_evaluator import evaluate_e2e
from evaluation.evaluators.model_evaluator import evaluate_model
from evaluation.io import load_dataset, write_report


def test_offline_model_evaluation_passes_quality_gates():
    report = evaluate_model(load_dataset("model"), "fixture")
    assert report.overall_status == "PASS"
    assert report.metrics["field_level_accuracy"]["rate"] == 1.0
    assert report.quality_gates["llm_final_decisions_zero"] is True


def test_component_evaluation_attributes_and_passes_all_checks():
    report = evaluate_components(load_dataset("component"))
    assert report.overall_status == "PASS"
    assert report.metrics["safety_critical_pass_rate"]["rate"] == 1.0


def test_e2e_evaluation_preserves_human_and_safety_boundaries():
    report = evaluate_e2e(load_dataset("e2e"))
    assert report.overall_status == "PASS"
    assert report.metrics["exact_routing_accuracy"]["rate"] >= 0.8
    assert report.quality_gates["human_boundary_100_percent"] is True
    assert report.quality_gates["ai_final_decisions_zero"] is True


def test_report_writer_omits_claim_text_and_pii(tmp_path):
    report = evaluate_e2e(load_dataset("e2e"))
    report_path, log_path = write_report(report, tmp_path)
    text = report_path.read_text(encoding="utf-8") + log_path.read_text(encoding="utf-8")
    assert "claim_description" not in text
    assert "customer" not in text
