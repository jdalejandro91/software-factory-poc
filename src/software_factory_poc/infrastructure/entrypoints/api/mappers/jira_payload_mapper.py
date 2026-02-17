import re
from typing import Any

import yaml

from software_factory_poc.core.domain.mission.entities import Mission, TaskDescription, TaskUser
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)


class JiraPayloadMapper:
    """
    Transforms Raw Jira Webhook Payloads into Domain Entities (Task).
    Handles Parsing of embedded configurations (YAML/Markdown/JiraMarkup).
    """

    # Combined Regex for Markdown (```) and Jira ({code})
    # Supports:
    # - ```yaml, ```scaffolder, ```
    # - {code:yaml}, {code:scaffolder}, {code}
    # - {code:yaml|borderStyle=solid} (Attributes)
    # Robust Pattern: Handles attributes by matching any char until closing brace logic
    CODE_BLOCK_PATTERN = re.compile(
        r"(?:```(?:scaffolder|yaml|yml)?|\{code(?:[:|][^\}]*)?\})\s*([\s\S]*?)\s*(?:```|\{code\})",
        re.IGNORECASE | re.DOTALL
    )

    @classmethod
    def to_domain(cls, payload: dict | JiraWebhookDTO) -> Mission:
        """
        Maps a Jira Payload to a Task Domain Entity.
        Performs one-pass parsing of the description.
        """
        # 1. Normalize Input to Dict for safe access if needed, or use DTO fields
        if isinstance(payload, JiraWebhookDTO):
            # Extract fields from DTO
            issue = payload.issue
            fields = issue.fields or object() # Safe access fallback
            
            key = issue.key
            summary = getattr(fields, "summary", "No Summary")
            description_text = getattr(fields, "description", "") or ""
            
            # Resolve Project
            project = getattr(fields, "project", None) or getattr(issue, "project", None)
            project_key = project.key if project else "UNKNOWN"

            # Resolve User
            user_dto = payload.user
            reporter = TaskUser(
                name=user_dto.name or "unknown",
                display_name=user_dto.display_name or "Unknown User",
                active=user_dto.active if user_dto.active is not None else True,
                # email is not always present in webhook, depends on privacy settings
            )
            
            event_type = payload.webhook_event or "unknown"
            timestamp = payload.timestamp or 0
            obj_id = issue.id or "0"
            status = "unknown" # Status might be nested, keeping simple for now
            issue_type = "Task" # Default

        else:
            # Fallback for Dict input
            issue = payload.get("issue", {})
            fields = issue.get("fields", {})
            
            key = issue.get("key", "UNKNOWN")
            summary = fields.get("summary", "No Summary")
            description_text = fields.get("description", "") or ""
            
            project = fields.get("project") or issue.get("project") or {}
            project_key = project.get("key", "UNKNOWN")
            
            user_data = payload.get("user", {})
            reporter = TaskUser(
                name=user_data.get("name", "unknown"),
                display_name=user_data.get("displayName", "Unknown User"),
                active=user_data.get("active", True)
            )
            
            event_type = payload.get("webhookEvent", "unknown")
            timestamp = payload.get("timestamp", 0)
            obj_id = issue.get("id", "0")
            status = fields.get("status", {}).get("name", "unknown")
            issue_type = fields.get("issuetype", {}).get("name", "Task")

        logger.info(f"Processing Issue {key}: Parsing Description ({len(description_text)} chars)")

        # 2. Parse Description (Regex + YAML)
        parsing_result = cls._parse_description_config(description_text)

        # 3. Construct Domain Entity
        task = Mission(
            id=obj_id,
            key=key,
            event_type=event_type,
            status=status,
            summary=summary,
            project_key=project_key,
            issue_type=issue_type,
            created_at=timestamp,
            reporter=reporter,
            description=parsing_result
        )

        logger.info(f"✅ Domain Task Created: {task.key} | Config Found: {len(task.description.config) > 0}")
        return task

    @classmethod
    def _parse_description_config(cls, text: str) -> TaskDescription:
        """
        Extracts YAML config from text using robust Regex.
        Separates the configuration block from the human-readable text.
        """
        logger.info(f"� Scanning Description ({len(text)} chars) for Config Block...")
        match = cls.CODE_BLOCK_PATTERN.search(text)
        logger.info(f"🧩 Match Found: {bool(match)}")
        
        config: dict[str, Any] = {}
        clean_text = text

        if match:
            # Extract content
            raw_yaml = match.group(1)
            
            # Sanitize Invisible Characters (Jira Artifacts)
            clean_yaml = raw_yaml.replace('\xa0', ' ').strip()
            
            try:
                parsed = yaml.safe_load(clean_yaml)
                if isinstance(parsed, dict):
                    config = parsed
                else:
                    logger.warning("Parsed YAML is not a dictionary. Ignoring.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML block in description: {e}")
            
            # Remove the configuration block from the raw text
            # We replace the *entire match* (delimiters + content) with empty string
            clean_text = text.replace(match.group(0), "").strip()
            logger.info("✂️  Config Block STRIPPED successfully.")
        else:
            logger.debug("No configuration block found in description.")

        return TaskDescription(
            raw_content=clean_text,
            config=config
        )


    @classmethod
    def _parse_description_config(cls, text: str) -> TaskDescription:
        """
        Extracts YAML config from text using robust Regex.
        Separates the configuration block from the human-readable text.
        """
        match = cls.CODE_BLOCK_PATTERN.search(text)
        config: dict[str, Any] = {}
        clean_text = text

        if match:
            # Extract content
            raw_yaml = match.group(1)
            
            # Sanitize Invisible Characters (Jira Artifacts)
            clean_yaml = raw_yaml.replace('\xa0', ' ').strip()
            
            try:
                parsed = yaml.safe_load(clean_yaml)
                if isinstance(parsed, dict):
                    config = parsed
                else:
                    logger.warning("Parsed YAML is not a dictionary. Ignoring.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML block in description: {e}")
            
            # Remove the configuration block from the raw text
            # We replace the *entire match* (delimiters + content) with empty string
            clean_text = text.replace(match.group(0), "").strip()
        else:
            logger.debug("No configuration block found in description.")

        return TaskDescription(
            raw_content=clean_text,
            config=config
        )
