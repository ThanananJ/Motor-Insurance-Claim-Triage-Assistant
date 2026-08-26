# Motor Insurance Claim Triage Assistant

Prototype decision-support system for initial motor-insurance claim triage.
The assistant will summarize claims, ground assessments in the provided policy,
identify missing information and risk signals, and recommend a routing path.

The Claim Officer remains responsible for every final claim decision.

## Current status

P0 deterministic claim analysis is implemented and covered by unit tests. It
accepts validated structured facts, checks Policy-required documents, evaluates
covered events and explicit exclusions, handles validated risk signals, and
returns a controlled routing recommendation.

Local LLM provider integration, exact Policy prompt grounding, structured
semantic extraction, validation, and safe fallback are implemented. A local
model must be selected and configured before live inference can run. Generated
summary/explanation composition and Gradio UI behavior are not yet implemented.

Run deterministic tests with:

```powershell
uv sync
uv run pytest -q
```

## Planned stack

- Python 3.11+
- Gradio frontend with chatbot and structured claim panels
- Ollama + Local LLM as the primary MVP runtime
- `langchain-ollama` as the planned Ollama communication layer
- Pydantic structured validation
- `uv` project, environment, and dependency management
- pytest for deterministic tests
- Gemini or another cloud LLM as an optional/future provider

## Implementation status

- **Implemented:** Pydantic contracts, tested P0 deterministic core, Ollama
  provider adapter, exact-Policy semantic extraction, and safe failure results.
- **Planned:** Grounded result composition/explanation and Gradio UI.

Live semantic extraction requires an existing Ollama service and an explicitly
configured `OLLAMA_MODEL`. The application never downloads or silently selects
a model. `OLLAMA_BASE_URL` and `OLLAMA_TIMEOUT_SECONDS` are also configurable.

`pyproject.toml` is the dependency source of truth. `requirements.txt` remains
only as a compatibility notice so dependency definitions are not duplicated.

See `docs/solution-design.md` for the solution architecture and
`docs/limitations-and-roadmap.md` for scope boundaries and roadmap.
