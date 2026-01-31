from __future__ import annotations

from software_factory_poc.application.core.agents.common.exceptions.infra_error import InfraError


class DependencyError(InfraError):
    """Raised when an optional provider dependency is missing."""
