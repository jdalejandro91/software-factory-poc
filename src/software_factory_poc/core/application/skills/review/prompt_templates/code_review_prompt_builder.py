from software_factory_poc.core.domain.mission import Mission


class CodeReviewPromptBuilder:
    """Builds hardened code review prompts with XML-delimited user data."""

    @staticmethod
    def build_system_prompt() -> str:
        return (
            "You are a Senior Software Architect and strict Code Reviewer for BrahMAS.\n"
            "Audit the Merge Request using the five evaluation dimensions below.\n"
            "Be rigorous with architecture, but constructive with suggestions."
        )

    @staticmethod
    def build_analysis_prompt(
        mission: Mission,
        mr_diff: str,
        conventions: str,
        code_review_params: dict[str, str] | None = None,
    ) -> str:
        """Build the user prompt with XML-delimited inputs.

        Args:
            mission: Full domain Mission entity.
            mr_diff: Raw git diff of the merge request.
            conventions: Architecture/conventions context from docs.
            code_review_params: Optional parsed YAML params (mr_url, branch, etc.).
        """
        sections = [
            _goal_section(mission, code_review_params),
            _input_data_section(mission, mr_diff, conventions),
            _evaluation_dimensions_section(),
            _constraints_section(),
            _output_schema_section(),
            _anti_examples_section(),
        ]
        return "\n\n".join(sections)


# ── Module-level helpers (each <=14 lines) ────────────────────────────


def _goal_section(mission: Mission, params: dict[str, str] | None) -> str:
    mr_url = (params or {}).get("mr_url", "N/A")
    branch = (params or {}).get("branch", "N/A")
    return (
        "## GOAL\n"
        f"Review the Merge Request for ticket **{mission.key}** "
        f"(project {mission.project_key}, type {mission.issue_type}).\n"
        f"MR URL: `{mr_url}` | Branch: `{branch}`"
    )


def _input_data_section(mission: Mission, mr_diff: str, conventions: str) -> str:
    return (
        "## INPUT DATA\n"
        f"<jira_summary>{mission.summary}</jira_summary>\n\n"
        f"<jira_description>{mission.description.raw_content}</jira_description>\n\n"
        f"<conventions>{conventions}</conventions>\n\n"
        f"<mr_diff>\n{mr_diff}\n</mr_diff>"
    )


def _evaluation_dimensions_section() -> str:
    return (
        "## EVALUATION DIMENSIONS\n"
        "Evaluate the code across these five dimensions:\n"
        "1. **Correctness**: Does the code satisfy the Jira requirement?\n"
        "2. **Security (OWASP)**: SQL injection, XSS, secrets in code, insecure deserialization.\n"
        "3. **SOLID / Clean Code**: SRP, OCP, DIP, naming, method size, cyclomatic complexity.\n"
        "4. **API Usage**: Correct use of frameworks, libraries, and external service contracts.\n"
        "5. **Tests & Documentation**: Test coverage for new logic, updated docstrings/READMEs."
    )


def _constraints_section() -> str:
    return (
        "## CONSTRAINTS\n"
        "1. Set `is_approved` to false if ANY critical issue is found.\n"
        "2. Each issue MUST reference the exact file path and line number when possible.\n"
        "3. Suggestions must be actionable — include corrected code snippets.\n"
        "4. Do NOT invent files or lines not present in the diff.\n"
        "5. The summary must be concise (max 3 sentences)."
    )


def _output_schema_section() -> str:
    return (
        "## OUTPUT SCHEMA\n"
        "You MUST respond with a JSON object matching `CodeReviewResponseSchema`:\n\n"
        "| Field       | Type                | Description                               |\n"
        "|-------------|---------------------|-------------------------------------------|\n"
        "| is_approved | bool                | true if publishable, false if not          |\n"
        "| summary     | str                 | Executive summary of the analysis          |\n"
        "| issues      | list[CodeIssueSchema]| List of findings                          |\n\n"
        "Each `CodeIssueSchema`:\n\n"
        "| Field       | Type                          | Description                    |\n"
        "|-------------|-------------------------------|--------------------------------|\n"
        "| file_path   | str                           | Analyzed file path             |\n"
        "| line_number | int or null                   | Line of the issue              |\n"
        '| severity    | "CRITICAL"|"WARNING"|"SUGGESTION" | Finding severity            |\n'
        "| description | str                           | Technical explanation          |\n"
        "| suggestion  | str                           | Suggested fix or action        |\n\n"
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
        "- Do NOT return an empty issues list when problems are visible in the diff."
    )
