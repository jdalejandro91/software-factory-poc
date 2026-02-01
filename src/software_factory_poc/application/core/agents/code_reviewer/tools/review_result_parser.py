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
        # 1. Clean Markdown
        clean_text = self._clean_markdown(llm_output)
        
        # 2. Extract JSON substring
        json_str = self._extract_json_substring(clean_text)

        try:
            data = json.loads(json_str)
            return self._validate_dto(data)
        except (json.JSONDecodeError, ValidationError) as e:
            self.logger.error(f"Failed to parse review result: {e}. Output: {llm_output[:200]}...")
            return self._create_fallback_response(llm_output, str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error parsing review result: {e}")
            return self._create_fallback_response(llm_output, str(e))

    def _clean_markdown(self, text: str) -> str:
        # Match ```json ... ``` or just ``` ... ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _extract_json_substring(self, text: str) -> str:
        """
        Locates the first '{' and the last '}' to handle conversational text wrappers.
        """
        start = text.find("{")
        end = text.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        
        # If no braces found, return original text to let json.loads try (or fail)
        return text

    def _validate_dto(self, data: Dict) -> CodeReviewResultDTO:
        return CodeReviewResultDTO.model_validate(data)

    def _create_fallback_response(self, raw_output: str, error: str) -> CodeReviewResultDTO:
        """
        Returns a valid DTO indicating a system error, preserving flow continuity.
        """
        from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import (
            ReviewCommentDTO, ReviewSeverity
        )
        
        return CodeReviewResultDTO(
            summary="Review Failed: AI Output Parsing Error",
            score=0,
            comments=[
                ReviewCommentDTO(
                    file_path="SYSTEM",
                    line_number=0,
                    comment_body=f"Failed to parse LLM response. Error: {error}. \n\nRaw Output Snippet:\n{raw_output[:500]}",
                    severity=ReviewSeverity.CRITICAL,
                    suggestion=None
                )
            ]
        )
