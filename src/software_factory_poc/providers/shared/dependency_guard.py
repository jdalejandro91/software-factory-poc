from __future__ import annotations

from dataclasses import dataclass

from llm_bridge.core.exceptions.dependency_error import DependencyError


@dataclass(frozen=True, slots=True)
class DependencyGuard:
    package: str
    extra: str

    def require(self) -> None:
        raise DependencyError(f"Missing dependency '{self.package}'. Install extra: llm-bridge[{self.extra}]")
