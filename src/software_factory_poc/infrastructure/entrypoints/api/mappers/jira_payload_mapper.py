import re
from typing import Any

import structlog
import yaml

from software_factory_poc.core.domain.mission import Mission, TaskDescription, TaskUser
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import (
    JiraUserDTO,
    JiraWebhookDTO,
)

logger = structlog.get_logger()


class JiraPayloadMapper:
    """Transforms Raw Jira Webhook Payloads into Domain Entities (Mission).

    Handles Parsing of embedded configurations (YAML/Markdown/JiraMarkup).
    """

    CODE_BLOCK_PATTERN = re.compile(
        r"(?:```(?:scaffolder|yaml|yml)?|\{code(?:[:|][^\}]*)?\})\s*([\s\S]*?)\s*(?:```|\{code\})",
        re.IGNORECASE | re.DOTALL,
    )

    # ── Public entry point ────────────────────────────────────────

    @classmethod
    def to_domain(cls, payload: dict[str, Any] | JiraWebhookDTO) -> Mission:
        """Map a Jira Payload to a Mission domain entity."""
        if isinstance(payload, JiraWebhookDTO):
            return cls._from_dto(payload)
        return cls._from_dict(payload)

    # ── DTO-based extraction ──────────────────────────────────────

    @classmethod
    def _from_dto(cls, payload: JiraWebhookDTO) -> Mission:
        """Build a Mission from a validated JiraWebhookDTO."""
        issue = payload.issue
        fields = issue.fields or object()
        description_text = getattr(fields, "description", "") or ""
        logger.info(
            "Parsing issue description",
            issue_key=issue.key,
            description_length=len(description_text),
        )
        mission = Mission(
            id=issue.id or "0",
            key=issue.key,
            event_type=payload.webhook_event or "unknown",
            status="unknown",
            summary=getattr(fields, "summary", "No Summary"),
            project_key=cls._resolve_dto_project_key(fields, issue),
            issue_type="Task",
            created_at=payload.timestamp or 0,
            reporter=cls._build_dto_reporter(payload.user),
            description=cls._parse_description_config(description_text),
        )
        logger.info(
            "Domain Mission created",
            mission_key=mission.key,
            config_found=bool(mission.description.config),
        )
        return mission

    @staticmethod
    def _resolve_dto_project_key(fields: Any, issue: Any) -> str:
        """Resolve project key from DTO fields or issue fallback."""
        project = getattr(fields, "project", None) or getattr(issue, "project", None)
        return project.key if project else "UNKNOWN"

    @staticmethod
    def _build_dto_reporter(user_dto: JiraUserDTO | None) -> TaskUser:
        """Build a TaskUser from the DTO's user field."""
        if user_dto is None:
            return TaskUser(name="unknown", display_name="Unknown User", active=True)
        return TaskUser(
            name=user_dto.name or "unknown",
            display_name=user_dto.display_name or "Unknown User",
            active=user_dto.active if user_dto.active is not None else True,
        )

    # ── Dict-based extraction (legacy fallback) ───────────────────

    @classmethod
    def _from_dict(cls, payload: dict[str, Any]) -> Mission:
        """Build a Mission from a raw dict payload."""
        issue_data = payload.get("issue", {})
        fields = issue_data.get("fields", {})
        description_text = fields.get("description", "") or ""
        logger.info(
            "Parsing issue description",
            issue_key=issue_data.get("key", "UNKNOWN"),
            description_length=len(description_text),
        )
        mission = Mission(
            id=issue_data.get("id", "0"),
            key=issue_data.get("key", "UNKNOWN"),
            event_type=payload.get("webhookEvent", "unknown"),
            status=fields.get("status", {}).get("name", "unknown"),
            summary=fields.get("summary", "No Summary"),
            project_key=cls._resolve_dict_project_key(fields, issue_data),
            issue_type=fields.get("issuetype", {}).get("name", "Task"),
            created_at=payload.get("timestamp", 0),
            reporter=cls._build_dict_reporter(payload.get("user", {})),
            description=cls._parse_description_config(description_text),
        )
        logger.info(
            "Domain Mission created",
            mission_key=mission.key,
            config_found=bool(mission.description.config),
        )
        return mission

    @staticmethod
    def _resolve_dict_project_key(fields: dict[str, Any], issue_data: dict[str, Any]) -> str:
        """Resolve project key from nested dict structures."""
        project = fields.get("project") or issue_data.get("project") or {}
        return str(project.get("key", "UNKNOWN"))

    @staticmethod
    def _build_dict_reporter(user_data: dict[str, Any]) -> TaskUser:
        """Build a TaskUser from a raw dict."""
        return TaskUser(
            name=user_data.get("name", "unknown"),
            display_name=user_data.get("displayName", "Unknown User"),
            active=user_data.get("active", True),
        )

    # ── Description parsing ───────────────────────────────────────

    @classmethod
    def _parse_description_config(cls, text: str) -> TaskDescription:
        """Extract YAML config from text, separating config block from human text."""
        match = cls.CODE_BLOCK_PATTERN.search(text)
        if not match:
            return TaskDescription(raw_content=text, config={})
        config = cls._try_parse_yaml(match.group(1))
        clean_text = text.replace(match.group(0), "").strip()
        return TaskDescription(raw_content=clean_text, config=config)

    @staticmethod
    def _try_parse_yaml(raw_yaml: str) -> dict[str, Any]:
        """Attempt YAML parsing with sanitization, returning empty dict on failure."""
        clean_yaml = raw_yaml.replace("\xa0", " ").strip()
        try:
            parsed = yaml.safe_load(clean_yaml)
            if isinstance(parsed, dict):
                return parsed
            logger.warning("Parsed YAML is not a dictionary — ignoring")
            return {}
        except yaml.YAMLError as exc:
            logger.warning(
                "Failed to parse YAML block", error_type="YAMLError", error_details=str(exc)
            )
            return {}
