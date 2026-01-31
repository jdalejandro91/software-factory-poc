from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ScaffoldingPromptBuilder:
    """
    Tool responsible for constructing the prompt for the Reasoner Agent.
    Optimized for dynamic architectural styles and strict separation of config vs. logic structure.
    """

    def build_prompt(self, request: ScaffoldingOrder, knowledge_context: str) -> str:
        knowledge_context = self._validate_context(knowledge_context, request.issue_key)

        system_section = self._get_role_definition(request)
        context_section = self._format_rag_context(knowledge_context)
        task_section = self._format_task_instructions(request)
        example_section = self._get_example_output()

        full_prompt = f"{system_section}\n{context_section}\n{task_section}\n{example_section}"

        logger.info(f"--- [DEBUG] SUPER PROMPT GENERATED ({request.issue_key}) ---")
        return full_prompt

    def _validate_context(self, context: str, issue_key: str) -> str:
        if not context or not context.strip():
            logger.warning(f"Generating prompt for {issue_key} WITHOUT Knowledge Context.")
            return "Use standard enterprise best practices for the requested architecture."
        return context

    def _get_role_definition(self, request: ScaffoldingOrder) -> str:
        return (
            f"ROLE: You are an Elite Software Architect specializing in {request.technology_stack}.\n"
            f"MISSION: Define the complete directory structure and configuration for a project named '{request.issue_key}'.\n"
        )

    def _format_rag_context(self, context: str) -> str:
        return (
            f"--- ARCHITECTURAL GUIDELINES (MUST FOLLOW) ---\n"
            f"{context}\n"
            f"----------------------------------------------\n"
        )

    def _format_task_instructions(self, request: ScaffoldingOrder) -> str:
        return (
            f"--- TASK INSTRUCTIONS ---\n"
            f"PROJECT GOAL: {request.summary}\n"
            f"TECH STACK: {request.technology_stack}\n"
            f"METADATA: {request.raw_instruction}\n\n"

            f"--- ARCHITECTURE STRATEGY ---\n"
            f"1. **Analyze the Architecture**: Determine the best pattern (DDD, Hexagonal, MVC, Modular Monolith) based on the 'TECH STACK' and 'PROJECT GOAL'.\n"
            f"2. **Exhaustive Structure**: You MUST generate the FULL, deep directory tree for that specific architecture. Do not leave any layer out (e.g., if DDD, include domain, application, infra, interface adapters).\n\n"

            f"--- CONTENT GENERATION RULES (CRITICAL) ---\n"
            f"Rule A: **ROOT CONFIGURATION FILES** (REAL CONTENT)\n"
            f"   - Files like `Dockerfile`, `.gitlab-ci.yml`, `.gitignore`, `pyproject.toml`/`package.json`, `Makefile`, `README.md` (root) MUST contain **valid, production-ready code**.\n"
            f"   - The Dockerfile must adhere to best practices (multi-stage builds, non-root user).\n"
            f"   - The CI pipeline must map to the project stages.\n\n"

            f"Rule B: **ARCHITECTURAL PACKAGES** (README ONLY - NO LOGIC)\n"
            f"   - Do NOT generate Python/TS implementation files (no empty classes, no 'pass').\n"
            f"   - Instead, inside EVERY architectural folder (e.g., `src/domain/`, `src/controllers/`), generate a single `README.md`.\n"
            f"   - This `README.md` must describe exactly what files/classes should be placed in that package by developers later.\n"
            f"   - Example: In `src/domain/repositories/README.md`, write: 'This package contains repository interfaces defining data access contracts.'\n\n"

            f"Rule C: **FORMAT**\n"
            f"   - Return ONLY a valid JSON list of objects. No markdown fencing.\n"
        )

    def _get_example_output(self) -> str:
        # Generic example that shows the *pattern* without biasing the *architecture*.
        return (
            f"--- EXAMPLE OUTPUT FORMAT (JSON ONLY) ---\n"
            f"[\n"
            f"  {{\"path\": \".gitignore\", \"content\": \"__pycache__/\\n*.env\\n.venv/\"}},\n"
            f"  {{\"path\": \"Dockerfile\", \"content\": \"FROM python:3.11-slim as builder... (full valid content)\"}},\n"
            f"  {{\"path\": \".gitlab-ci.yml\", \"content\": \"stages:\\n  - test... (full valid content)\"}},\n"
            f"  {{\"path\": \"README.md\", \"content\": \"# Project Name\\n\\nArchitecture: [Selected Architecture]\\n...\"}},\n"
            f"  {{\"path\": \"src/README.md\", \"content\": \"Source code root.\"}},\n"
            f"  {{\"path\": \"src/core/README.md\", \"content\": \"Contains core business rules and entities.\"}},\n"
            f"  {{\"path\": \"src/adapters/http/README.md\", \"content\": \"Contains API controllers and route handlers.\"}},\n"
            f"  {{\"path\": \"tests/README.md\", \"content\": \"Unit and integration tests go here.\"}}\n"
            f"]\n"
        )