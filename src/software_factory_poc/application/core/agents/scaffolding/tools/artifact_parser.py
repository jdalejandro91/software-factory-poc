import re
import json
import logging
from typing import List, Any
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.common.exceptions.contract_parse_error import ContractParseError
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class ArtifactParser:
    """
    Tool responsible for parsing the raw text response from the LLM 
    into structured FileContent objects.
    """

    def parse_response(self, response_text: str) -> List[FileContentDTO]:
        """
        Parses JSON response. Handles markdown code blocks.
        """
        cleaned_text = self._clean_markdown(response_text)
        
        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Offending text: {cleaned_text}")
            raise ContractParseError(message=f"Invalid JSON format: {e}", original_text=response_text)

        if not isinstance(data, list):
             raise ContractParseError(message="Response must be a list of objects", original_text=response_text)

        parsed_files: List[FileContentDTO] = []
        for item in data:
             if not isinstance(item, dict):
                 continue
                 
             path = item.get("path")
             content = item.get("content")
             
             if not path:
                 logger.warning("Skipping item without path")
                 continue
                 
             # Security check
             if ".." in path or path.startswith("/"):
                 logger.warning(f"Skipping invalid path: {path}")
                 continue
             
             if not content:
                 content = ""
                 
             parsed_files.append(FileContentDTO(path=path, content=content))
        
        return parsed_files

    def _clean_markdown(self, text: str) -> str:
        # Remove ```json and ``` wrapping
        pattern = r"^```(?:json)?\s*(.*?)\s*```$"
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
        return text.strip()
