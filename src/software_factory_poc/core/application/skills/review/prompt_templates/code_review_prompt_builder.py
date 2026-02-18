import json
from typing import Any

from software_factory_poc.core.domain.mission import Mission


class CodeReviewPromptBuilder:
    """Builds hardened code review prompts split into system + user messages.

    Returns separate system and user prompts with XML-delimited sections
    to prevent prompt injection and maximise LLM compliance.
    """

    # ── System Prompt ──────────────────────────────────────────────

    @staticmethod
    def build_system_prompt() -> str:
        """Compose the full system prompt from role, rules, schema, and anti-examples."""
        sections = [
            _system_role_section(),
            _strict_rules_section(),
            _output_schema_section(),
            _anti_examples_section(),
        ]
        return "\n\n".join(sections)

    # ── User Prompt ────────────────────────────────────────────────

    @staticmethod
    def build_analysis_prompt(
        mission: Mission,
        mr_diff: str,
        conventions: str,
        code_review_params: dict[str, str] | None = None,
        repository_tree: str = "",
    ) -> str:
        """Build the user prompt with XML-delimited inputs."""
        sections = [
            _mission_requirements_section(mission, code_review_params),
            _architecture_standards_section(conventions),
        ]
        if repository_tree:
            sections.append(_repository_tree_section(repository_tree))
        sections.append(_merge_request_diffs_section(mr_diff))
        sections.append(_final_instruction_section())
        return "\n\n".join(sections)


# ── System Prompt Helpers (each <=14 lines) ──────────────────────────


def _system_role_section() -> str:
    return (
        "<system_role>\n"
        "Eres BrahMAS Quality Gatekeeper, un implacable Staff DevSecOps Engineer. "
        "Tu objetivo es auditar un Merge Request con precision quirurgica.\n"
        "</system_role>"
    )


def _strict_rules_section() -> str:
    return (
        "<strict_rules>\n"
        "1. FORMATO: Retorna UNICAMENTE un JSON valido que cumpla con el esquema "
        "CodeReviewResponseSchema. Cero wrappers de markdown.\n"
        "2. ENFOQUE: Ignora estilos de formateo (eso lo hace el linter). Enfocate en "
        "violaciones a los estandares de arquitectura, principios SOLID, inyecciones "
        "de seguridad (OWASP) y acoplamiento.\n"
        "3. PRECISION ABSOLUTA: Tienes ESTRICTAMENTE PROHIBIDO alucinar errores o lineas. "
        "Cada hallazgo debe anclarse a un `file_path` y `line_number` que exista "
        "EXPLICITAMENTE dentro de los `<merge_request_diffs>`.\n"
        "4. SEVERIDAD: Usa unicamente CRITICAL, WARNING, SUGGESTION. Fugas de secretos "
        "o inyeccion SQL son CRITICAL.\n"
        "</strict_rules>"
    )


def _output_schema_section() -> str:
    return (
        "## OUTPUT SCHEMA\n"
        "You MUST respond with a JSON object matching `CodeReviewResponseSchema`:\n\n"
        "| Field       | Type                 | Description                               |\n"
        "|-------------|----------------------|-------------------------------------------|\n"
        "| is_approved | bool                 | true if publishable, false if not          |\n"
        "| summary     | str                  | Executive summary of the analysis          |\n"
        "| issues      | list[CodeIssueSchema]| List of findings                           |\n\n"
        "Each `CodeIssueSchema`:\n\n"
        "| Field       | Type                              | Description                    |\n"
        "|-------------|-----------------------------------|--------------------------------|\n"
        "| file_path   | str                               | Analyzed file path             |\n"
        "| line_number | int or null                       | Line of the issue              |\n"
        '| severity    | "CRITICAL"|"WARNING"|"SUGGESTION" | Finding severity               |\n'
        "| description | str                               | Technical explanation          |\n"
        "| suggestion  | str                               | Suggested fix or action        |\n\n"
        "### Valid JSON example\n"
        "```json\n"
        "{\n"
        '  "is_approved": false,\n'
        '  "summary": "Critical SQL injection found in auth module.",\n'
        '  "issues": [\n'
        "    {\n"
        '      "file_path": "src/auth.py",\n'
        '      "line_number": 42,\n'
        '      "severity": "CRITICAL",\n'
        '      "description": "Raw string interpolation in SQL query.",\n'
        '      "suggestion": "Use parameterized queries: cursor.execute(\\"SELECT ...\\", (param,))"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```"
    )


def _anti_examples_section() -> str:
    return (
        "## ANTI-EXAMPLES (do NOT do this)\n"
        "- Do NOT set `is_approved: true` when critical issues exist.\n"
        "- Do NOT reference files or lines not present in the diff.\n"
        "- Do NOT provide vague suggestions like 'improve this code'.\n"
        "- Do NOT return an empty issues list when problems are visible in the diff.\n"
        "- Do NOT wrap JSON in markdown code blocks."
    )


# ── User Prompt Helpers (each <=14 lines) ────────────────────────────


def _mission_requirements_section(mission: Mission, params: dict[str, str] | None) -> str:
    mr_url = (params or {}).get("mr_url", "N/A")
    branch = (params or {}).get("branch", "N/A")
    config: dict[str, Any] = {
        "ticket": mission.key,
        "project": mission.project_key,
        "type": mission.issue_type,
        "mr_url": mr_url,
        "branch": branch,
    }
    return (
        "<mission_requirements>\n"
        f"{json.dumps(config, indent=2)}\n\n"
        f"<jira_summary>{mission.summary}</jira_summary>\n\n"
        f"<jira_description>{mission.description.raw_content}</jira_description>\n"
        "</mission_requirements>"
    )


def _architecture_standards_section(conventions: str) -> str:
    return f"<architecture_standards>\n{conventions}\n</architecture_standards>"


def _repository_tree_section(repo_tree: str) -> str:
    return f"<repository_tree>\n{repo_tree}\n</repository_tree>"


def _merge_request_diffs_section(mr_diff: str) -> str:
    return f"<merge_request_diffs>\n{mr_diff}\n</merge_request_diffs>"


def _final_instruction_section() -> str:
    return (
        "INSTRUCCION: Realiza la revision estructurada. Si el diff cumple "
        "perfectamente con todo, retorna una lista de hallazgos vacia y aprueba."
    )
