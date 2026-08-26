from pathlib import Path

import pytest

from src.policy.loader import PolicyLoadError, PolicyLoader
from src.policy.retriever import ExactPolicyRetriever, PolicyRetriever


def test_exact_policy_context_can_be_loaded(claim_factory):
    loader = PolicyLoader()
    policy = loader.load_exact()
    retrieved = ExactPolicyRetriever(loader).retrieve(claim_factory())
    assert retrieved == policy
    assert "Claim filed more than 30 days after the incident without valid reason" in policy


def test_exact_retriever_satisfies_provider_independent_protocol():
    assert isinstance(ExactPolicyRetriever(), PolicyRetriever)


def test_missing_policy_file_is_controlled(tmp_path: Path):
    loader = PolicyLoader(tmp_path / "missing-policy.md")
    with pytest.raises(PolicyLoadError, match="Unable to load Policy source"):
        loader.load_exact()
