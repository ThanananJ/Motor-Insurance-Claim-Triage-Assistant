# Demo Runbook

## Start

```powershell
uv sync
uv run python app.py
```

Open the localhost URL shown in the terminal.

## Recommended Demo

Use Assignment Case 4. It clearly demonstrates AI-assisted extraction, human
verification, validated risk signals, deterministic Fraud review routing, and
the final human decision boundary.

## Case 4 Steps

1. Load Assignment Case 4.
2. Analyze Claim with AI.
3. Review the AI proposal.
4. Correct or confirm `repeated_claims = TRUE`, `severe_damage = TRUE`, and
   `weak_evidence = TRUE`.
5. Check Human Confirmation.
6. Run triage.
7. Show the risk signals, Fraud review recommendation, deterministic reasoning,
   and Human Final Decision reminder.

## Safety Demo

Optionally show Case 5. Correct any unsupported AI fact, preserve uncertainty
where the evidence does not support a value, and show the Manual review result.

## If Ollama Fails

Continue with the UNKNOWN proposal, enter or correct the facts manually,
confirm them, and run deterministic triage.

## Key Presenter Message

> AI proposes semantic facts. The Claim Officer verifies them. Deterministic
> rules apply the Policy. The Claim Officer makes the final decision.
