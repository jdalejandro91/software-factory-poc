import json
import re
from typing import Dict

from pydantic import ValidationError

from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import CodeReviewResultDTO
from software_factory_poc.application.core.agents.code_reviewer.exceptions.review_parsing_error import ReviewParsingError
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


class ReviewResultParser:
    def __init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)

    def parse(self, llm_output: str) -> CodeReviewResultDTO:
        try:
            cleaned_json = self._clean_markdown(llm_output)
            data = self._parse_json(cleaned_json)
            return self._validate_dto(data)
        except (json.JSONDecodeError, ValidationError) as e:
            self.logger.error(f"Failed to parse review result: {e}")
            raise ReviewParsingError(f"Parsing failed: {e}", llm_output) from e
        except Exception as e:
            self.logger.error(f"Unexpected error parsing review result: {e}")
            raise ReviewParsingError(f"Unexpected error: {e}", llm_output) from e

    def _clean_markdown(self, text: str) -> str:
        # Match ```json ... ``` or just ``` ... ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _parse_json(self, text: str) -> Dict:
        return json.loads(text)

    def _validate_dto(self, data: Dict) -> CodeReviewResultDTO:
        return CodeReviewResultDTO.model_validate(data)
