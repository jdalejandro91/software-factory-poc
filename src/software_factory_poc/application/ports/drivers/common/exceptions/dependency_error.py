from __future__ import annotations

from software_factory_poc.application.ports.drivers.common.exceptions.infra_error import InfraError


class DependencyError(InfraError):
    """Raised when an optional provider dependency is missing."""
