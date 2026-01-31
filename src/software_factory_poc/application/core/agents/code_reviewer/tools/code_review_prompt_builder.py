from typing import List

from software_factory_poc.application.core.agents.common.dtos.change_type import ChangeType
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


class CodeReviewPromptBuilder:
    def __init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)

    def build_prompt(
        self,
        diffs: List[FileChangesDTO],
        original_files: List[FileContentDTO],
        technical_context: str,
        requirements: str
    ) -> str:
        """Builds the prompt for the code review orchestration."""
        prompt_parts = [
            self._get_system_role(),
            self._format_requirements(requirements),
            self._format_technical_context(technical_context),
            self._format_diffs(diffs),
            self._format_file_context(original_files, diffs),
            self._get_output_schema()
        ]
        
        full_prompt = "\n\n".join(prompt_parts)
        self.logger.info(f"Generated prompt with length: {len(full_prompt)} characters")
        return full_prompt

    def _get_system_role(self) -> str:
        return (
            "You are a Senior Software Architect & Security Expert reviewing code changes.\n"
            "Your goal is to identify bugs, security vulnerabilities, design flaws, and code style issues.\n"
            "Focus on logical correctness, performance, and maintainability."
        )

    def _format_requirements(self, reqs: str) -> str:
        return f"## Requirements / Task Description\n{reqs}"

    def _format_technical_context(self, context: str) -> str:
        return f"## Technical Context\n{context}"

    def _format_diffs(self, diffs: List[FileChangesDTO]) -> str:
        parts = ["## Code Changes (Diffs)"]
        for diff in diffs:
            parts.append(f"File: {diff.file_path}")
            parts.append(f"Type: {diff.change_type.name}")
            parts.append(f"Diff:\n{diff.diff_content}\n" + "-"*40)
        return "\n".join(parts)

    def _format_file_context(self, files: List[FileContentDTO], diffs: List[FileChangesDTO]) -> str:
        parts = ["## Additional File Context"]
        changed_paths = {d.file_path for d in diffs}
        if diffs:
             for d in diffs:
                 if d.old_path:
                     changed_paths.add(d.old_path)

        for file in files:
            if file.path in changed_paths:
                continue
            
            content = file.content or ""
            if len(content) > 2000:
                content = content[:2000] + "\n[...Content Truncated...]"
            
            parts.append(f"File: {file.path}\nContent:\n{content}\n" + "-"*40)
        
        return "\n".join(parts)

    def _get_output_schema(self) -> str:
        return (
            "## Output Schema\n"
            "Return a JSON object with the following structure:\n"
            "{\n"
            '  "summary": "Brief executive summary of findings",\n'
            '  "verdict": "APPROVE | COMMENT | REQUEST_CHANGES",\n'
            '  "comments": [\n'
            "    {\n"
            '      "file_path": "path/to/file",\n'
            '      "line_number": <int>,\n'
            '      "severity": "INFO | MINOR | MAJOR | CRITICAL",\n'
            '      "comment_body": "Detailed explanation",\n'
            '      "suggestion": "code replacement only (optional)"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "IMPORTANT: 'suggestion' must contain ONLY the code to replace the target lines, without markdown blocks."
        )
