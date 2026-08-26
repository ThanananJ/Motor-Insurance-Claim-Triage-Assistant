"""Load the immutable assignment Policy as exact text."""

from __future__ import annotations

from pathlib import Path


DEFAULT_POLICY_PATH = Path(__file__).parents[2] / "data" / "policy_rules.md"


class PolicyLoadError(RuntimeError):
    pass


class PolicyLoader:
    def __init__(self, policy_path: Path = DEFAULT_POLICY_PATH) -> None:
        self._policy_path = policy_path

    @property
    def policy_path(self) -> Path:
        return self._policy_path

    def load_exact(self) -> str:
        try:
            policy = self._policy_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PolicyLoadError(f"Unable to load Policy source: {self._policy_path}") from exc
        if not policy.strip():
            raise PolicyLoadError("Policy source is empty")
        return policy
