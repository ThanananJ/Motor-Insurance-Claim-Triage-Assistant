"""MVP exact-context retriever abstraction; no vector RAG is used."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.policy.loader import PolicyLoader
from src.schemas import ClaimInput


@runtime_checkable
class PolicyRetriever(Protocol):
    def retrieve(self, claim: ClaimInput) -> str: ...


class ExactPolicyRetriever:
    """Return the complete approved Policy because the MVP source is small."""

    def __init__(self, loader: PolicyLoader | None = None) -> None:
        self._loader = loader or PolicyLoader()

    def retrieve(self, claim: ClaimInput) -> str:
        del claim  # Retrieval abstraction retains the future claim-aware signature.
        return self._loader.load_exact()
