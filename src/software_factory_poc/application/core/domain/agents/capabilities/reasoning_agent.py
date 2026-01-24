from abc import ABC, abstractmethod
from typing import List
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.ports.gateways.dtos import FileContent

class ReasoningAgent(ABC):
    """
    Capability contract for Agents responsible for Generating Code/Reasoning.
    Focuses on WHAT: transforming a request + context into code files.
    """
    
    @abstractmethod
    def generate_scaffolding(self, request: ScaffoldingRequest, context: str) -> List[FileContent]:
        """
        Generates the scaffolding files based on the request and architectural context.
        Encapsulates prompt engineering, LLM invocation, and parsing.
        """
        pass
