"""CLI entry point for all three evaluation levels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.evaluators.component_evaluator import evaluate_components
from evaluation.evaluators.e2e_evaluator import evaluate_e2e
from evaluation.evaluators.model_evaluator import evaluate_model
from evaluation.io import RESULTS, load_dataset, write_report


def _live_provider():
    from src.config import AppConfig
    from src.llm.ollama_provider import OllamaProvider
    return OllamaProvider(AppConfig.from_env())


def _summary(reports, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Evaluation Summary", "", "Static policy grounding is used; Retrieval Evaluation is not applicable in the current implementation.", "", "| Level | Mode | Status | Passed | Total |", "|---|---|---:|---:|---:|"]
    for report in reports:
        passed = report.metrics["status_counts"].get("PASS", 0)
        lines.append(f"| {report.evaluation_level} | {report.mode} | {report.overall_status} | {passed} | {report.metrics['total_cases']} |")
    lines += ["", "## Quality gates", ""]
    for report in reports:
        lines.append(f"### {report.evaluation_level.title()}")
        lines += [f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in report.quality_gates.items()]
        lines.append("")
    path = output_dir / "latest-summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=["model", "component", "e2e", "all"], default="all")
    parser.add_argument("--mode", choices=["fixture", "offline", "live"], default="fixture")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=RESULTS)
    args = parser.parse_args(argv)
    if args.runs < 1: parser.error("--runs must be at least 1")
    reports = []
    levels = ["model", "component", "e2e"] if args.level == "all" else [args.level]
    provider = None
    if "model" in levels and args.mode == "live":
        try: provider = _live_provider()
        except Exception as exc:
            unavailable_error = exc
            class Unavailable:
                provider_name = "ollama"
                model_name = None
                def invoke_structured(self, prompt, schema): raise unavailable_error
            provider = Unavailable()
    for level in levels:
        dataset = load_dataset(level)
        if level == "model": report = evaluate_model(dataset, "fixture" if args.mode == "offline" else args.mode, provider, args.runs)
        elif level == "component": report = evaluate_components(dataset)
        else:
            if args.mode == "live":
                from src.policy.retriever import ExactPolicyRetriever
                from src.services.focused_claim_extractor import FocusedClaimExtractor
                live = provider or _live_provider()
                report = evaluate_e2e(dataset, mode="live", extractor=FocusedClaimExtractor(live, ExactPolicyRetriever()))
            else:
                report = evaluate_e2e(dataset)
        write_report(report, args.output_dir)
        reports.append(report)
        print(json.dumps({"level": level, "status": report.overall_status, "metrics": report.metrics}, ensure_ascii=False))
    summary = _summary(reports, args.output_dir)
    print(f"Summary: {summary}")
    return 0 if all(r.overall_status in {"PASS", "SKIPPED"} for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
