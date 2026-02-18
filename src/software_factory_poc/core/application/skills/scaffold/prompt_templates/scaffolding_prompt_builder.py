import json
import logging
from typing import Any

from software_factory_poc.core.domain.mission import Mission

logger = logging.getLogger(__name__)


class ScaffoldingPromptBuilder:
    """Builds a hardened scaffolding prompt split into system + user messages.

    Returns ``(system_prompt, user_prompt)`` with XML-delimited sections
    to prevent prompt injection and maximise LLM compliance.
    """

    def build_prompt_from_mission(
        self, mission: Mission, knowledge_context: str
    ) -> tuple[str, str]:
        """Build the (system_prompt, user_prompt) pair from a Domain Mission."""
        knowledge_context = self._validate_context(knowledge_context)
        config = mission.description.config
        tech_stack = config.get("technology_stack", "unknown")

        system_prompt = self._build_system_prompt(tech_stack)
        user_prompt = self._build_user_prompt(mission, knowledge_context, tech_stack)

        logger.info("Prompt generated for mission %s, stack: %s", mission.key, tech_stack)
        return system_prompt, user_prompt

    # ── System Prompt Sections (each <=14 lines) ──────────────────

    @staticmethod
    def _build_system_prompt(tech_stack: str) -> str:
        """Compose the full system prompt from identity, rules, schema, and anti-examples."""
        sections = [
            ScaffoldingPromptBuilder._system_role_section(tech_stack),
            ScaffoldingPromptBuilder._strict_rules_section(),
            ScaffoldingPromptBuilder._output_schema_section(),
            ScaffoldingPromptBuilder._anti_examples_section(),
        ]
        return "\n\n".join(sections)

    @staticmethod
    def _system_role_section(tech_stack: str) -> str:
        return (
            "<system_role>\n"
            "You are BrahMAS Sovereign Scaffolder, an Elite Enterprise Software Architect "
            f"specializing in {tech_stack}. Your SOLE purpose is to generate deterministic, "
            "production-ready bootstrapping source code.\n"
            "</system_role>"
        )

    @staticmethod
    def _strict_rules_section() -> str:
        return (
            "<strict_rules>\n"
            "1. OUTPUT FORMAT: Return ONLY a valid JSON object that matches the requested "
            "Pydantic schema. No prose, no explanations.\n"
            "2. ZERO MARKDOWN: Do NOT wrap JSON in markdown code blocks.\n"
            "3. ZERO PLACEHOLDERS: Generate complete, functional code — no TODO comments.\n"
            "4. SECURITY: Never generate hardcoded credentials, tokens, or secrets.\n"
            "5. RELATIVE PATHS: All paths MUST be relative to the repository root.\n"
            "6. BRANCH NAMING: Branch name MUST start with `feature/` followed by the ticket key.\n"
            "7. CONVENTIONAL COMMITS: Commit message MUST follow Conventional Commits format.\n"
            "</strict_rules>"
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

    # ── User Prompt Sections (each <=14 lines) ───────────────────

    @staticmethod
    def _build_user_prompt(mission: Mission, knowledge_context: str, tech_stack: str) -> str:
        """Compose the full user prompt from mission intent, tech stack, and architecture."""
        sections = [
            ScaffoldingPromptBuilder._mission_intent_section(mission),
            ScaffoldingPromptBuilder._technology_stack_section(mission, tech_stack),
            ScaffoldingPromptBuilder._architecture_standards_section(knowledge_context),
        ]
        return "\n\n".join(sections)

    @staticmethod
    def _mission_intent_section(mission: Mission) -> str:
        service_name = mission.description.config.get("parameters", {}).get(
            "service_name", mission.key
        )
        target = mission.description.config.get("target", {})
        project_path = target.get("gitlab_project_path", "N/A")
        return (
            "<mission_intent>\n"
            f"Ticket: {mission.key} | Project: {mission.project_key} | "
            f"Type: {mission.issue_type}\n"
            f"Service: {service_name} | Repository: {project_path}\n\n"
            f"<jira_summary>{mission.summary}</jira_summary>\n\n"
            f"<jira_description>{mission.description.raw_content}</jira_description>\n"
            "</mission_intent>"
        )

    @staticmethod
    def _technology_stack_section(mission: Mission, tech_stack: str) -> str:
        config = mission.description.config
        params = config.get("parameters", {})
        target = config.get("target", {})
        config_payload: dict[str, Any] = {
            "technology_stack": tech_stack,
            "parameters": params,
            "target": target,
        }
        return f"<technology_stack>\n{json.dumps(config_payload, indent=2)}\n</technology_stack>"

    @staticmethod
    def _architecture_standards_section(knowledge_context: str) -> str:
        return (
            "<architecture_standards>\n"
            "The text below defines the MANDATORY architecture standards.\n"
            "You MUST extract the folder structure defined here.\n\n"
            f"<architecture_context>{knowledge_context}</architecture_context>\n"
            "</architecture_standards>"
        )

    # ── Shared Helpers ────────────────────────────────────────────

    @staticmethod
    def _validate_context(context: str) -> str:
        if not context or not context.strip():
            return "No specific documentation provided. Follow standard best practices."
        return context
