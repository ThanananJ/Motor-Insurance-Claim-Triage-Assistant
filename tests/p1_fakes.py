from __future__ import annotations

from typing import Any

from src.llm.base import LLMProviderError
from src.schemas import ClaimFacts


def complete_fact_data(**overrides: Any) -> dict[str, str]:
    data = ClaimFacts().model_dump(mode="json")
    data.update(overrides)
    return data


def extraction_payload(**fact_overrides: Any) -> dict[str, Any]:
    return {"facts": complete_fact_data(**fact_overrides), "evidence": []}


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-semantic-model"

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = extraction_payload() if response is None else response
        self.error = error
        self.prompts: list[str] = []
        self.schemas: list[type] = []

    def invoke_structured(self, prompt: str, schema: type) -> Any:
        self.prompts.append(prompt)
        self.schemas.append(schema)
        if self.error:
            raise self.error
        return self.response


class FakeProviderFailure(LLMProviderError):
    code = "fake_unavailable"


class FixedPolicyRetriever:
    def __init__(self, policy: str = "EXACT TEST POLICY") -> None:
        self.policy = policy

    def retrieve(self, claim) -> str:
        del claim
        return self.policy
