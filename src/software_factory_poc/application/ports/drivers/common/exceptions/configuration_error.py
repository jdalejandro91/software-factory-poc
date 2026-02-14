from __future__ import annotations

from software_factory_poc.application.ports.drivers.common.exceptions.infra_error import InfraError


class ConfigurationError(InfraError):
    """Raised when configuration is invalid or incomplete."""
