# Motor Insurance Claim Triage Assistant

Local Hybrid AI prototype for initial motor-insurance claim triage.

## Overview

The application uses an Ollama Local LLM to propose semantic facts from claim
text. A Claim Officer must review, correct, and explicitly confirm those facts
before deterministic Policy, document, coverage, risk, and routing logic runs.

The result is a triage recommendation—not a final approval, rejection, fraud
decision, or payment authorization. The Human Claim Officer remains the final
decision maker.

## Architecture / How It Works

```text
Claim Information
    → Local LLM Semantic Extraction
    → AI Suggested Facts
    → Human Review & Confirmation
    → Deterministic Policy / Rule / Risk Evaluation
    → Triage Recommendation
    → Human Final Decision
```

# Getting Started

The commands below use the repository's actual configuration:

- Python `3.11` from `.python-version`; `pyproject.toml` requires Python `>=3.11`
- dependencies locked in `uv.lock`
- Ollama at `http://localhost:11434`
- advisory model `qwen2.5:3b`
- Gradio entry point `app.py`

## 1. Clone the Repository

```bash
git clone https://github.com/ThanananJ/Motor-Insurance-Claim-Triage-Assistant.git
cd Motor-Insurance-Claim-Triage-Assistant
```

Verify Git:

```bash
git --version
```

## 2. Install the Prerequisites

| Tool | Repository requirement | Verify |
|---|---|---|
| Git | Required to clone the project; no version is pinned | `git --version` |
| Python | `3.11` selected by `.python-version`; project supports `>=3.11` | `python --version` |
| uv | Required for the locked environment; no uv version is pinned | `uv --version` |
| Ollama | Required for real Local LLM suggestions; no version is pinned | `ollama --version` |

### Install uv

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart the terminal if necessary, then verify:

```bash
uv --version
```

See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
for package-manager alternatives.

## 3. Prepare Python and the Environment File

Install the repository-selected Python version through uv if it is unavailable:

```bash
uv python install 3.11
```

Verify which interpreter the project will use:

```bash
uv python find 3.11
```

Create the local environment file from the committed example.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

The default file is aligned with the tested MVP:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_MODEL=qwen2.5:3b
```

Do not commit `.env`.

## 4. Sync Dependencies

From the repository root, create/update `.venv` and install the exact locked
dependencies, including pytest:

```bash
uv sync --locked
```

Verify the environment:

```bash
uv run python --version
```

You do not need to activate `.venv`; every project command below uses `uv run`.
The runtime dependencies are Gradio, `langchain-ollama`, and Pydantic. The
development dependency is pytest. `pyproject.toml` and `uv.lock` are the
dependency sources of truth.

## 5. Install and Start Ollama

### Windows

```powershell
irm https://ollama.com/install.ps1 | iex
```

Ollama for Windows normally runs in the background and serves its API on
`http://localhost:11434`. If it is not running, start the Ollama application
from the Windows Start menu.

### macOS

Install and launch the application from the
[official Ollama download](https://ollama.com/download). The application runs
the local service in the background.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start the installed system service, or run this in a separate terminal:

```bash
ollama serve
```

Official platform details are available for
[Windows](https://docs.ollama.com/windows),
[macOS](https://docs.ollama.com/macos), and
[Linux](https://docs.ollama.com/linux).

Verify the CLI and local service:

```bash
ollama --version
ollama list
```

## 6. Download the Local Model

Pull the exact model configured in `.env.example`:

```bash
ollama pull qwen2.5:3b
```

Confirm it is installed:

```bash
ollama list
```

The model is advisory. Its output must pass Pydantic validation and Human
Review / Confirmation before deterministic triage. Model quality and latency
depend on local CPU, GPU, and RAM.

## 7. Run the Prototype

Make sure Ollama is running, then execute from the repository root:

```bash
uv run python app.py
```

Keep this terminal open while using the application. Stop it with `Ctrl+C`.

## 8. Open the Web UI

Open the local URL printed by Gradio, for example:

```text
* Running on local URL:  http://127.0.0.1:7860
```

The port may differ when `7860` is occupied, so always use the URL printed in
your terminal.

1. Select Assignment Case 1–5 or enter a custom claim.
2. Click **Analyze Claim with AI**.
3. Review and correct all **AI Suggested Facts**.
4. Check the mandatory Human Confirmation box.
5. Click **Confirm Facts & Run Triage**.
6. Review coverage, Missing Information, Risk Signals, routing, reasoning, and
   Prototype Confidence Level.
7. The Claim Officer makes the final decision.

## 9. Run Automated Tests

Ollama is not required for the automated regression suite; provider behavior is
mocked where appropriate.

```bash
uv run pytest -q
```

Current verified baseline:

```text
118 passed, 0 failed, 0 warnings
```

## 10. Troubleshooting

### `uv` is not recognized

Restart the terminal and run `uv --version`. If it is still unavailable, use
an installation method from the
[official uv guide](https://docs.astral.sh/uv/getting-started/installation/).

### Python 3.11 is unavailable or the wrong Python is selected

```bash
uv python install 3.11
uv python find 3.11
uv sync --locked
uv run python --version
```

The final command must report a version compatible with `>=3.11`; uv normally
follows the repository's `.python-version` value of `3.11`.

### `.env` or `OLLAMA_MODEL` is missing

Recreate `.env` from `.env.example` using the command in Step 3 and confirm it
contains `OLLAMA_MODEL=qwen2.5:3b`.

### The application cannot connect to Ollama

```bash
ollama --version
ollama list
```

- Windows/macOS: launch or restart the Ollama desktop application.
- Linux: start the service or run `ollama serve` in another terminal.
- Confirm `.env` contains `OLLAMA_BASE_URL=http://localhost:11434`.

### `qwen2.5:3b` is not installed

```bash
ollama pull qwen2.5:3b
ollama list
```

### Local inference times out

Inference speed depends on hardware. Increase the positive numeric value of
`OLLAMA_TIMEOUT_SECONDS` in `.env` if the model needs more than 60 seconds,
then restart the prototype.

### AI Suggested Facts are UNKNOWN or imperfect

UNKNOWN is a supported safety state, not an application error. Ollama,
validation, or semantic uncertainty can produce UNKNOWN values. Review/correct
the fields, explicitly confirm them, and continue to deterministic triage.
Unconfirmed AI output never drives routing.

### The localhost page does not open

Use the exact `Running on local URL` value in the application terminal. Gradio
may select another port when `7860` is occupied. Confirm that the terminal
running `uv run python app.py` is still open.

### Tests cannot find dependencies

```bash
uv sync --locked
uv run pytest -q
```

## Project Structure

```text
app.py                  Gradio entry point
data/                   immutable Policy and Assignment cases
docs/                   design, limitations, and demo documentation
prompts/                prompt design and extraction templates
results/                historical and final evaluation results
scripts/                controlled Local LLM evaluation tools
src/
  llm/                  provider integration
  policy/               exact Policy loading and retrieval
  rules/                deterministic document/coverage/risk/routing logic
  services/             extraction and confirmed workflow orchestration
  orchestrator.py       deterministic triage composition
  schemas.py            Pydantic contracts
tests/                  automated tests
```

## Additional Documentation

- [`docs/solution-design.md`](docs/solution-design.md) — architecture and
  responsibility boundaries
- [`prompts/prompt-design.md`](prompts/prompt-design.md) — prompt and structured
  output design
- [`docs/demo-runbook.md`](docs/demo-runbook.md) — presentation workflow
- [`docs/limitations-and-roadmap.md`](docs/limitations-and-roadmap.md) — MVP
  limitations and future work
- [`results/test-results.md`](results/test-results.md) — evaluation evidence
