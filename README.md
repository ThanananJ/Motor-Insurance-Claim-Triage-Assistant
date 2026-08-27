# Motor Insurance Claim Triage Assistant

## Overview

A local Hybrid AI prototype that helps a Motor Insurance Claim Officer perform
initial claim triage. The Local LLM proposes semantic facts; the officer must
review and correct them before deterministic Policy engines calculate coverage,
missing documents, risk signals, and a routing recommendation.

The Claim Officer remains the final decision maker. The application cannot
approve/reject a claim, confirm fraud, or authorize payment.

## Business Problems

- Check whether submitted claim documents satisfy Policy requirements.
- Apply coverage and exclusion conditions consistently, including exact date
  calculation.
- Surface suspicious/inconsistent evidence and Policy risk indicators without
  turning them into an autonomous fraud conclusion.

The MVP checks document presence. OCR and document-authenticity/image-forensic
analysis are future work.

## Solution Architecture

```text
Gradio Claim Input
    ↓
Ollama Local LLM + Exact Policy Context
    ↓
Pydantic-validated Semantic Fact Proposal
    ↓
Mandatory Claim Officer Review / Correction
    ↓
ConfirmedClaimFacts
    ↓
Deterministic Document / Coverage / Date / Risk / Routing Engines
    ↓
Structured Recommendation
    ↓
Human Claim Officer Final Decision
```

The configured Local LLM is advisory and untrusted. Gradio uses the two-stage
`TriageService`; unconfirmed model facts cannot enter the deterministic core.

## Tech Stack

- Python 3.11+
- Gradio frontend
- Ollama + Local LLM runtime
- `langchain-ollama` provider integration
- Pydantic structured validation
- Exact Policy Context grounding
- Python deterministic Rule/Risk engines
- `uv` dependency and project management
- pytest testing

Cloud LLM providers and production RAG/vector search are optional future work,
not implemented prototype dependencies.

## Project Structure

```text
app.py                  Gradio entry point
data/                   immutable Policy and Assignment cases
docs/                   solution design, limitations, demo runbook
prompts/                prompt design and extraction templates
results/                historical and final validation results
scripts/                controlled local-model evaluation harnesses
src/
  llm/                  provider integration
  policy/               exact Policy loading/retrieval
  rules/                deterministic engines
  services/             extraction and confirmed orchestration
  orchestrator.py       P0 deterministic composition
  schemas.py            Pydantic contracts
tests/                  automated tests
```

`CODEX_HANDOFF.md` and `CODEX_PROTOTYPE_INSTRUCTIONS_with_policy.md` are
git-ignored development-coordination files and are not submission artifacts.
Local `.env`, virtual environments, caches, and Ollama model binaries are not
tracked.

## Setup

From the repository root:

```powershell
uv sync
```

`pyproject.toml` and `uv.lock` are the dependency source of truth.
`requirements.txt` is a compatibility notice only.

## Ollama Configuration

Ollama is optional for generating AI suggestions; the safe manual workflow
still works if inference is unavailable. To use local inference, start the
existing Ollama service and ensure the configured model is already installed:

```powershell
ollama --version
ollama list
ollama ps
```

Copy `.env.example` to a local `.env` and configure:

```text
LLM_PROVIDER
OLLAMA_BASE_URL
OLLAMA_MODEL
OLLAMA_TIMEOUT_SECONDS
```

Do not commit `.env`. The tested presentation environment used `qwen2.5:3b` as
an advisory model; it is not accepted as an autonomous extractor.

## Run Prototype

```powershell
uv run python app.py
```

Open the localhost Gradio URL printed in the terminal. No public share link is
created. If Ollama fails, all AI facts safely fall back to UNKNOWN so the Claim
Officer can enter/correct them, confirm, and continue with deterministic triage.

## Run Tests

```powershell
uv run pytest -q
```

Final validated baseline: **115 passed, 0 failed, 0 warnings**.

## Demo Flow

1. Load an Assignment Case or enter a claim.
2. Analyze Claim with AI.
3. Review and correct every proposed fact.
4. Check the mandatory Human Confirmation box.
5. Run deterministic triage.
6. Inspect coverage, documents, risk signals, routing, and reasoning.
7. The Claim Officer makes the final decision.

See `docs/demo-runbook.md` for the short presentation flow.

## Assignment Cases

| Case | Final prototype routing |
|---|---|
| 1 | Manual review |
| 2 | Rejection review |
| 3 | Manual review |
| 4 | Fraud review |
| 5 | Manual review |

Human Confirmation may be required to correct imperfect Local LLM proposals;
the expected route is never injected into runtime logic.

## Documentation

- `docs/solution-design.md` — implemented architecture and assignment mapping
- `prompts/prompt-design.md` — prompt and structured-output boundaries
- `results/test-results.md` — historical experiments and final evidence
- `docs/limitations-and-roadmap.md` — prototype limitations and future work
- `docs/demo-runbook.md` — presenter instructions
