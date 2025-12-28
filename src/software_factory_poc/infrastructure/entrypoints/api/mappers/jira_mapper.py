import re
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

class JiraMapper:
    def map_webhook_to_command(self, dto: JiraWebhookDTO) -> ScaffoldingRequest:
        description = dto.issue.fields.description if dto.issue.fields else ""
        raw_instruction = self._extract_scaffolding_block(description or "")
        
        return ScaffoldingRequest(
            ticket_id=dto.issue.key,
            project_key=dto.issue.key.split("-")[0] if "-" in dto.issue.key else "",
            summary=dto.issue.fields.summary or "" if dto.issue.fields else "",
            raw_instruction=raw_instruction,
            requester=dto.user.display_name or dto.user.name or "unknown" if dto.user else "unknown"
        )

    def _extract_scaffolding_block(self, text: str) -> str:
        if not text:
            return ""

        # Pattern: ```scaffolding ... ```
        # Case insensitive for 'scaffolding' tag
        scaffold_pattern = r"```scaffolding\s*(.*?)\s*```"
        match = re.search(scaffold_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Fallback: Generic markdown block if scaffolding specific not found?
        # User requirement was specific: "extract the code block ```scaffolding ... ```"
        # But to avoid breaking existing "yaml" or "json" blocks usage if that was the intent,
        # checking parser service code: it handled `{code}`, ` ``` `, ` ```yaml `.
        # I should probably try to be flexible but prioritize `scaffolding`.
        
        # Fallback to generic ``` or ```yaml
        generic_pattern = r"```(?:[\w]+)?\s*(.*?)\s*```"
        match_gen = re.search(generic_pattern, text, re.DOTALL)
        if match_gen:
             # Logic to differentiate? If multiple blocks exist? 
             # Assuming single block or first block.
             return match_gen.group(1).strip()
             
        # Jira Wiki Code
        jira_wiki_pattern = r"\{code(?:[:\w]+)?\}\s*(.*?)\s*\{code\}"
        match_wiki = re.search(jira_wiki_pattern, text, re.DOTALL | re.IGNORECASE)
        if match_wiki:
            return match_wiki.group(1).strip()

        return ""
