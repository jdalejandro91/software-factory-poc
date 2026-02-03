from abc import ABC, abstractmethod

from software_factory_poc.application.core.agents.research.dtos.project_context_dto import (
    ProjectContextDTO,
)


class ResearchGateway(ABC):
    @abstractmethod
    def retrieve_context(self, query: str) -> str:
        """
        Retrieves relevant context based on search criteria.
        """
        raise NotImplementedError

    @abstractmethod
    def get_page_content(self, page_id: str) -> str:
        """
        Retrieves content by specific Page ID.
        """
        raise NotImplementedError

    @abstractmethod
    def get_project_context(self, project_name: str) -> ProjectContextDTO:
        """
        Recupera recursivamente el contexto técnico de un proyecto buscando en la 
        jerarquía de páginas (simulando la ruta /projects/<project_name>).
        """
        raise NotImplementedError
