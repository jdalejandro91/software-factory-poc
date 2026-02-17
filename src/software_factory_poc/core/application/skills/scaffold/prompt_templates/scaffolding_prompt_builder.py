import json
import logging
from typing import Any

from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


class ScaffoldingPromptBuilder:
    """Builds a hardened scaffolding prompt with XML-delimited user data."""

    def build_prompt_from_mission(self, mission: Mission, knowledge_context: str) -> str:
        """Builds prompt using the Domain Mission Entity."""
        knowledge_context = self._validate_context(knowledge_context)

        config = mission.description.config
        tech_stack = config.get("technology_stack", "unknown")
        service_name = config.get("parameters", {}).get("service_name", mission.key)

        sections = [
            self._role_section(tech_stack),
            self._goal_section(mission, service_name),
            self._input_data_section(mission),
            self._architecture_context_section(knowledge_context),
            self._hard_constraints_section(),
            self._output_schema_section(),
            self._anti_examples_section(),
        ]

        prompt = "\n\n".join(sections)
        logger.info("Prompt generated for mission %s, stack: %s", mission.key, tech_stack)
        return prompt

    # ── Private Composed Methods (each <=14 lines) ────────────────────

    @staticmethod
    def _validate_context(context: str) -> str:
        if not context or not context.strip():
            return "No specific documentation provided. Follow standard best practices."
        return context

    @staticmethod
    def _role_section(tech_stack: str) -> str:
        return (
            "## ROLE\n"
            f"You are a Principal Software Architect specializing in **{tech_stack}**.\n"
            "You generate production-ready project scaffolding that strictly follows "
            "the architecture standards provided."
        )

    @staticmethod
    def _goal_section(mission: Mission, service_name: str) -> str:
        target = mission.description.config.get("target", {})
        project_path = target.get("gitlab_project_path", "N/A")
        return (
            "## GOAL\n"
            f"Generate the complete file structure for service **{service_name}** "
            f"(ticket {mission.key}, project {mission.project_key}, "
            f"type {mission.issue_type}).\n"
            f"Target repository: `{project_path}`."
        )

    @staticmethod
    def _input_data_section(mission: Mission) -> str:
        config = mission.description.config
        tech_stack = config.get("technology_stack", "unknown")
        params = config.get("parameters", {})
        target = config.get("target", {})

        config_payload: dict[str, Any] = {
            "technology_stack": tech_stack,
            "parameters": params,
            "target": target,
        }

        return (
            "## INPUT DATA\n"
            f"<jira_summary>{mission.summary}</jira_summary>\n\n"
            f"<jira_description>{mission.description.raw_content}</jira_description>\n\n"
            f"<mission_config>{json.dumps(config_payload, indent=2)}</mission_config>"
        )

    @staticmethod
    def _architecture_context_section(knowledge_context: str) -> str:
        return (
            "## ARCHITECTURE CONTEXT\n"
            "The text below defines the MANDATORY architecture standards.\n"
            "You MUST extract the folder structure defined here.\n\n"
            f"<architecture_context>{knowledge_context}</architecture_context>"
        )

    @staticmethod
    def _hard_constraints_section() -> str:
        return (
            "## HARD CONSTRAINTS\n"
            "1. Every generated file MUST have non-empty content.\n"
            "2. Paths MUST be relative to the repository root (no leading `/`).\n"
            "3. Do NOT include secrets, tokens, or real credentials.\n"
            "4. File extensions and config files MUST match the technology stack.\n"
            "5. Follow Conventional Commits for the commit message.\n"
            "6. The branch name MUST start with `feature/` followed by the ticket key."
        )

    @staticmethod
    def _output_schema_section() -> str:
        return (
            "## OUTPUT SCHEMA\n"
            "You MUST respond with a JSON object matching `ScaffoldingResponseSchema`:\n\n"
            "| Field           | Type               | Description                          |\n"
            "|-----------------|--------------------|------------------------------------- |\n"
            "| branch_name     | str                | e.g. feature/PROJ-123-service-name   |\n"
            "| commit_message  | str                | Conventional Commits format          |\n"
            "| files           | list[FileSchemaDTO]| Each with path, content, is_new      |\n\n"
            "Each `FileSchemaDTO`:\n\n"
            "| Field   | Type | Description                              |\n"
            "|---------|------|------------------------------------------|\n"
            "| path    | str  | Relative file path (e.g. src/main.py)    |\n"
            "| content | str  | Full generated file content              |\n"
            "| is_new  | bool | Always true for scaffolding               |\n\n"
            "### Valid JSON example\n"
            "```json\n"
            "{\n"
            '  "branch_name": "feature/PROJ-123-my-service",\n'
            '  "commit_message": "feat(PROJ-123): scaffold my-service project structure",\n'
            '  "files": [\n'
            '    {"path": ".gitignore", "content": "node_modules/\\ndist/", "is_new": true},\n'
            '    {"path": "src/main.ts", "content": "import { NestFactory } from ...",'
            ' "is_new": true}\n'
            "  ]\n"
            "}\n"
            "```"
        )

    @staticmethod
    def _anti_examples_section() -> str:
        return (
            "## ANTI-EXAMPLES (do NOT do this)\n"
            "- Do NOT return a bare JSON array `[{...}]` — return the full schema object.\n"
            "- Do NOT leave `content` empty or use placeholder text like `// TODO`.\n"
            "- Do NOT include absolute paths (e.g. `/home/user/project/src/main.py`).\n"
            "- Do NOT invent a technology stack different from the one specified."
        )
