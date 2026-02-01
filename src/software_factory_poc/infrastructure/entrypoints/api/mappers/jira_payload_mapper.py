from typing import Union

from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class JiraPayloadMapper:
    """
    Maps incoming Jira Webhook payloads to internal Domain Commands (ScaffoldingOrder).
    """

    @classmethod
    def map_to_request(cls, payload: Union[dict, JiraWebhookDTO]) -> ScaffoldingOrder:
        if isinstance(payload, JiraWebhookDTO):
            return cls._extract_from_dto(payload)
        return cls._extract_from_dict(payload)

    @classmethod
    def _extract_from_dto(cls, payload: JiraWebhookDTO) -> ScaffoldingOrder:
        issue_key = payload.issue.key
        raw_desc = payload.issue.fields.description or ""
        
        logger.info(f"Processing Task {issue_key}. Raw Description Length: {len(raw_desc)}")
        
        # 1. Parse Description for Scaffolding Block
        from software_factory_poc.infrastructure.entrypoints.api.parsers.jira_description_parser import JiraDescriptionParser
        task_desc = JiraDescriptionParser.parse(raw_desc)
        
        # 2. Extract Params
        params = task_desc.scaffolding_params or {}
        
        tech_stack = params.get("technology_stack", "nestJS")
        target_config = params.get("target", {})
        extra_params = params.get("parameters", {})
        
        # 3. Resolve Project Info Safely
        project_data = None
        # Priority 1: Project inside fields (Standard)
        if payload.issue.fields and payload.issue.fields.project:
            project_data = payload.issue.fields.project
        # Priority 2: Project at root (Automation/System)
        elif payload.issue.project:
            project_data = payload.issue.project
            
        p_key = project_data.key if project_data else "UNKNOWN"
        # Ensure ID is string (some payloads send it as int)
        p_id = str(project_data.id) if (project_data and hasattr(project_data, 'id') and project_data.id) else "0"

        # 4. Build Order
        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction=task_desc.human_text, # Use clean text
            technology_stack=tech_stack,
            target_config=target_config,
            extra_params=extra_params,
            summary=payload.issue.fields.summary,
            reporter=payload.user.display_name,
            project_key=p_key,
            project_id=p_id
        )

    @classmethod
    def _extract_from_dict(cls, payload: dict) -> ScaffoldingOrder:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        issue_key = issue.get("key", "UNKNOWN")
        raw_desc = fields.get("description", "")
        
        logger.info(f"Processing Task {issue_key}. Raw Description Length: {len(raw_desc)}")

        # 1. Parse Description
        from software_factory_poc.infrastructure.entrypoints.api.parsers.jira_description_parser import JiraDescriptionParser
        task_desc = JiraDescriptionParser.parse(raw_desc)
        
        # 2. Extract Params
        params = task_desc.scaffolding_params or {}
        
        # 3. Build Order
        return ScaffoldingOrder(
            issue_key=issue_key,
            raw_instruction=task_desc.human_text,
            technology_stack=params.get("technology_stack", "nestJS"),
            target_config=params.get("target", {}),
            extra_params=params.get("parameters", {}),
            summary=fields.get("summary", "No Summary"),
            reporter=payload.get("user", {}).get("displayName", "Unknown"),
            project_key=fields.get("project", {}).get("key", ""),
            project_id=fields.get("project", {}).get("id", "")
        )
