from dataclasses import dataclass
from typing import List
import logging

from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.llm_gateway import LlmGateway
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.ports.gateways.dtos import FileContent
from software_factory_poc.application.core.domain.services.prompt_builder_service import PromptBuilderService
from software_factory_poc.application.core.domain.services.file_parsing_service import FileParsingService
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError

@dataclass
class ReasoningAgent(BaseAgent):
    """
    Agent responsible for reasoning about the requirements and generating the scaffolding code.
    """
    llm_gateway: LlmGateway
    model_name: str = "gpt-4-turbo"

    def generate_scaffolding(self, request: ScaffoldingRequest, context: str) -> List[FileContent]:
        # 1. Build Prompt
        prompt = PromptBuilderService.build_scaffolding_prompt(request, context)
        
        # 2. Call LLM
        llm_response = self.llm_gateway.generate_code(prompt=prompt, model=self.model_name)
        
        # 3. Parse Response
        files = FileParsingService.parse_llm_response(llm_response)
        
        # 4. Validate
        if not files:
            raise DomainError("El Agente de Razonamiento generó una respuesta vacía o con formato inválido. No se encontraron bloques <<<FILE:path>>>.")
            
        return files
