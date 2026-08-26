# Prompt Design

This document defines the implementation-level design for semantic claim-fact
extraction. It complements the architecture summary in `docs/solution-design.md`.

## 1. System role and decision boundary

The model is an assistant for initial motor-insurance claim triage. It may
understand language and propose semantic facts supported by observable claim
evidence. It cannot approve or reject claims, select routing, calculate date
differences, decide document completeness, invent Policy Rules, or override the
deterministic core. The Claim Officer retains the final decision.

## 2. Exact Policy context

The complete text of `data/policy_rules.md` is loaded through the Policy Loader
and Exact Policy Retriever and injected into the extraction prompt. The Policy
is grounding context, not content the model may rewrite or expand. The MVP uses
the full exact context because it is small; embeddings and vector retrieval are
outside scope.

## 3. Claim context treated as untrusted data

`ClaimInput` is serialized as JSON and placed inside explicit untrusted-data
delimiters. The model is instructed that commands embedded in the claim
description or history are claim content and must not override system/task
instructions. Prompt isolation is one guardrail; schema validation,
deterministic rules, and human review provide additional protection.

## 4. Task instructions

The extraction task is narrow: populate all semantic fields in the strict
LLM-facing extraction schema, which is then converted into canonical
`ClaimFacts`.

- `TRUE` means the supplied claim evidence supports the fact.
- `FALSE` means the supplied evidence explicitly establishes the negative.
- `UNKNOWN` means neither state can be established.
- Explicit evidence takes priority over `UNKNOWN`; a supported fact must not be
  left unknown.
- Information not mentioned is always `UNKNOWN`, never silently `FALSE`.
- `event_type` maps only to the supported enum and is `unknown` when unclear.
- The model does not calculate submission delay. It extracts only whether a
  reason for late submission is explicitly supplied: a stated valid reason is
  `TRUE`, an explicit statement that no reason was provided is `FALSE`, and no
  mention of the topic is `UNKNOWN`.
- `repeated_claims` is a semantic fact. No numeric Policy threshold exists;
  explicit repeated/multiple claims is `TRUE`, explicit no prior claims is
  `FALSE`, and missing/ambiguous history is `UNKNOWN`. Assignment case counts
  are language evidence, not a reusable Policy Rule.
- Severe damage and weak evidence are extracted as separate semantic facts;
  this does not move deterministic document completeness into the LLM.

A small set of targeted examples clarifies theft, illegal racing, repeated
claims positive/negative, late-reason positive/negative, and unmentioned
UNKNOWN behavior. Assignment cases are not copied as demonstrations.

## 5. Structured output contract

The prompt includes the JSON schema generated from the flat
`LLMExtractionPayload`. It contains all semantic fields as required enum values
and no evidence list. Removing the nested facts/evidence generation burden
reduces output complexity for the 3B model and prevents evidence/fact
contradictions. The application validates this payload and converts it into the
unchanged canonical `ClaimFacts`; canonical evidence remains optional and is
empty for this extraction path. The schema has no approval, rejection, routing,
payment, document-completeness, or date-calculation field.

`langchain-ollama` requests Ollama JSON-schema output. The provider checks the
structured response, and the Claim Extractor validates it again with Pydantic.
Every canonical fact field must be present. Invalid enums, omitted fields,
malformed responses, provider failures, and validation failures produce a
controlled unsuccessful extraction with all semantic facts left `UNKNOWN`.
Malformed/schema-invalid output receives at most one corrective retry asking
only for all required fields and allowed enum values. Semantic disagreement
with an expected test answer never triggers a retry.

## Safe failure behavior

When Ollama or the configured model is unavailable, inference times out, or
structured validation fails, the application does not repair or invent facts.
It exposes extraction as unavailable/incomplete so later orchestration can run
reliable deterministic checks and preserve Manual/Human Review.
