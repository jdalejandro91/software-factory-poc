from software_factory_poc.application.drivers import ResearchProviderType
from software_factory_poc.application.drivers.research.ports.research_gateway import ResearchGateway
# from software_factory_poc.infrastructure.providers.research.filesystem_provider_impl import FileSystemProviderImpl # If we move it
from software_factory_poc.infrastructure.configuration.app_config import AppConfig
from software_factory_poc.infrastructure.drivers.research.confluence_provider_impl import ConfluenceProviderImpl


class ResearchProviderFactory:
    """
    Factory to build Research Providers based on configuration.
    """
    @staticmethod
    def build_research_gateway(config: AppConfig, provider_type: ResearchProviderType) -> ResearchGateway:
        if provider_type == ResearchProviderType.CONFLUENCE:
            return ConfluenceProviderImpl(config.confluence)
            
        # elif provider_type == ResearchProviderType.FILE_SYSTEM:
        #     return FileSystemProviderImpl(...)
            
        else:
             raise ValueError(f"Unsupported Research Provider: {provider_type}")
