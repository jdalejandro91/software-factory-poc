from pathlib import Path

from software_factory_poc.application.core.domain.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.agents.research.config.research_provider_type import ResearchProviderType
from software_factory_poc.application.core.domain.agents.research.ports.research_gateway import ResearchGateway



class FileSystemKnowledgeAdapter(ResearchGateway):
    """
    Adapter to retrieve knowledge (docs, templates) from the local filesystem.
    Useful for testing or local development mode.
    """
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def retrieve_context(self, query: str) -> str:
        """
        Retrieves content from a file.
        The 'query' is interpreted as a relative path to the file from the base_path.
        """
        # Security check: prevent directory traversal
        if ".." in query or query.startswith("/"):
             raise ProviderError(
                provider=ResearchProviderType.FILE_SYSTEM, # Or defining a generic FILE provider
                message=f"Invalid file query path: {query}. Traversal not allowed.",
                retryable=False
            )

        target_file = self.base_path / query
        
        if not target_file.exists():
             raise ProviderError(
                provider=ResearchProviderType.FILE_SYSTEM,
                message=f"File not found: {target_file}",
                retryable=False
            )
            
        if not target_file.is_file():
             raise ProviderError(
                provider=ResearchProviderType.FILE_SYSTEM,
                message=f"Target is not a file: {target_file}",
                retryable=False
            )

        try:
            return target_file.read_text(encoding="utf-8")
        except Exception as e:
            raise ProviderError(
                provider=ResearchProviderType.FILE_SYSTEM,
                message=f"Error reading file {target_file}: {e}",
                retryable=True 
            )
