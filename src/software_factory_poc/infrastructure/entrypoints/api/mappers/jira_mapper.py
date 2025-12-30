import re
from typing import Optional

from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

class JiraMapper:
    def map_webhook_to_command(self, dto: JiraWebhookDTO) -> ScaffoldingRequest:
        description = self._get_description(dto)
        raw_instruction = self._extract_scaffolding_block(description)
        
        return ScaffoldingRequest(
            issue_key=dto.issue.key,
            project_key=self._get_project_key(dto),
            summary=self._get_summary(dto),
            raw_instruction=raw_instruction,
            reporter=self._get_reporter(dto)
        )

    def _get_project_key(self, dto: JiraWebhookDTO) -> str:
        if dto.issue.fields and dto.issue.fields.project:
            return dto.issue.fields.project.key
        return "UNKNOWN"

    def _get_description(self, dto: JiraWebhookDTO) -> str:
        if dto.issue.fields and dto.issue.fields.description:
            return dto.issue.fields.description
        return ""

    def _get_summary(self, dto: JiraWebhookDTO) -> str:
        if dto.issue.fields and dto.issue.fields.summary:
            return dto.issue.fields.summary
        return ""

    def _get_reporter(self, dto: JiraWebhookDTO) -> str:
        if dto.user:
            return dto.user.display_name or dto.user.name or "unknown"
        return "unknown"

    def _extract_scaffolding_block(self, text: str) -> str:
        if not text:
            return ""
        
        content = self._match_regex(text, r"```scaffolding\s*(.*?)\s*```")
        if content:
            return content
            
        return self._fallback_extraction(text)

    def _fallback_extraction(self, text: str) -> str:
        # Fallback to generic ``` or ```yaml
        content = self._match_regex(text, r"```(?:[\w]+)?\s*(.*?)\s*```")
        if content:
            return content
            
        # Fallback to Jira Wiki Code
        return self._match_regex(text, r"\{code(?:[:\w]+)?\}\s*(.*?)\s*\{code\}") or ""

    def _match_regex(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
