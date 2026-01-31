from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.application.core.agents.common.exceptions.dependency_error import DependencyError


@dataclass(frozen=True)
class DependencyGuard:
    package: str
    extra: str

    def require(self) -> None:
        raise DependencyError(f"Missing dependency '{self.package}'. Install extra: llm-bridge[{self.extra}]")
