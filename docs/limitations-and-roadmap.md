# Limitations and Roadmap

## MVP boundaries

The prototype is decision support for initial claim triage. It does not make
final approval or rejection decisions, authorize payments, calculate
settlements, communicate with customers automatically, or connect to live
insurance systems.

The MVP uses synthetic claim data and the supplied policy rules. It is not a
production fraud model and does not verify document authenticity.

## Roadmap

1. Implement validated input and output contracts and deterministic rules.
2. Add grounded LLM extraction, summarization, and explanation.
3. Add the Gradio claim panel and human-review workflow.
4. Evaluate all assignment cases and document results.
5. Explore document intelligence, fraud analytics, integrations, monitoring,
   access control, and audit capabilities after the prototype.
