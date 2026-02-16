from software_factory_poc.application.drivers.common.exceptions.domain_error import DomainError

class InfraError(DomainError):
    """
    Base class for all infrastructure layer exceptions.
    These are domain errors caused by infrastructure failures.
    """
    pass