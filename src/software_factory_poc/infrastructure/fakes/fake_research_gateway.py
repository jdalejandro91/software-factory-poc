from datetime import datetime

from software_factory_poc.application.core.agents.research.dtos.document_content_dto import DocumentContentDTO
from software_factory_poc.application.core.agents.research.dtos.project_context_dto import ProjectContextDTO
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway


class FakeResearchGateway(ResearchGateway):
    """
    Fake implementation for testing/local development.
    Satisfies the ResearchGateway interface.
    """

    def retrieve_context(self, query: str) -> str:
        return f"Fake context for query: {query}. Standard architecture implies clean code."

    def get_page_content(self, page_id: str) -> str:
        return f"Fake content for page {page_id}. This is a mock document."

    def get_project_context(self, project_name: str) -> ProjectContextDTO:
        """
        Returns a hardcoded ProjectContextDTO for testing flow.
        """
        # Creación de Docs simulados
        doc1 = DocumentContentDTO(
            title="1. Reglas de Negocio Generales",
            url="http://fake-confluence/doc/1",
            content="<h1>Reglas Generales</h1><p>Todo el código debe seguir Clean Architecture. Los DTOs deben ser inmutables.</p>",
            metadata={"id": "doc-1", "space": "PROJ"}
        )
        
        doc2 = DocumentContentDTO(
            title="2. Guía de Estilos Python",
            url="http://fake-confluence/doc/2",
            content="<h1>Estilo Python</h1><p>Usar Type Hints estrictos. Seguir PEP-8. Usar Black formatter.</p>",
            metadata={"id": "doc-2", "space": "PROJ"}
        )
        
        return ProjectContextDTO(
            project_name=project_name,
            root_page_id="9999",
            documents=[doc1, doc2],
            retrieved_at=datetime.utcnow()
        )
