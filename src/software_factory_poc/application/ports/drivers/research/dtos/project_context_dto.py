from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from software_factory_poc.application.ports.drivers.research.dtos.document_content_dto import (
    DocumentContentDTO,
)


@dataclass
class ProjectContextDTO:
    """
    Aggregation of technical context for a specific project.
    Simulates a folder/hierarchy retrieval.
    """
    project_name: str
    root_page_id: str
    documents: List[DocumentContentDTO]
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_documents(self) -> int:
        return len(self.documents)
