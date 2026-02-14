import json
import re
from typing import List, Any

from software_factory_poc.application.ports.drivers.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.ports.drivers.common.exceptions import ContractParseError
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
        cleaned_text = self._clean_markdown_fences(response_text)
        data = self._parse_json_safely(cleaned_text, response_text)
        self._validate_structure_is_list(data, response_text)
        return self._convert_to_dtos(data)

    def _clean_markdown_fences(self, text: str) -> str:
        """Removes markdown code fences."""
        # Regex explanation:
        # ```(?:json)? : Match ``` optionally followed by json
        # \s* : Match any whitespace (newlines etc)
        # (.*?) : Match content minimal
        # \s* : Match trailing whitespace
        # ``` : Match closing fences
        # We drop anchors ^ $ to allow finding the block inside other text easily
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()

    def _parse_json_safely(self, clean_text: str, original_text: str) -> Any:
        """Parses JSON and handles errors."""
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ContractParseError(message=f"Invalid JSON format: {e}", original_text=original_text)

    def _validate_structure_is_list(self, data: Any, original_text: str) -> None:
        """Ensures the root element is a list."""
        if not isinstance(data, list):
             raise ContractParseError(message="Response must be a list of objects", original_text=original_text)

    def _convert_to_dtos(self, data: List[Any]) -> List[FileContentDTO]:
        """Converts raw list to DTOs with validation."""
        parsed_files: List[FileContentDTO] = []
        for item in data:
             if not isinstance(item, dict):
                 continue
                 
             path = item.get("path")
             content = item.get("content") or ""
             
             if not path:
                 logger.warning("Skipping item without path")
                 continue
                 
             if not self._is_safe_path(path):
                 logger.warning(f"Skipping invalid path: {path}")
                 continue
                 
             parsed_files.append(FileContentDTO(path=path, content=content))
        return parsed_files

    def _is_safe_path(self, path: str) -> bool:
        """Validates path security."""
        import os
        # Prevent absolute paths and traversal
        if os.path.isabs(path):
            return False
        if ".." in path:
            return False
        if path.startswith("/"):
            return False
        return True


