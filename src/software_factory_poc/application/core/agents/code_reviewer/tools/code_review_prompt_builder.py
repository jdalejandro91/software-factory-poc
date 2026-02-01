from typing import List

from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


class CodeReviewPromptBuilder:
    def __init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)

    MAX_CONTEXT_CHARS = 60000

    def build_prompt(
        self,
        diffs: List[FileChangesDTO],
        original_files: List[FileContentDTO],
        technical_context: str,
        requirements: str
    ) -> str:
        """Builds the prompt for the code review orchestration with strict token budgeting."""
        
        # 1. Prepare Static & High-Priority Components
        system_role = self._get_system_role()
        reqs_block = self._format_requirements(requirements)
        tech_block = self._format_technical_context(technical_context)
        schema_block = self._get_output_schema()
        diffs_block = self._format_diffs(diffs) # Priority 1: Diffs
        
        # 2. Calculate Used Budget
        # We assume 1 token ~= 4 chars, but we use strict char limit for simplicity
        current_usage = len(system_role) + len(reqs_block) + len(tech_block) + len(schema_block) + len(diffs_block)
        remaining_budget = self.MAX_CONTEXT_CHARS - current_usage
        
        self.logger.info(f"Prompt base usage: {current_usage} chars. Remaining budget for historical context: {remaining_budget} chars.")

        # 3. Fill Remainder with Historical Context
        file_context_block = ""
        if remaining_budget > 500: # Minimum useful context
            file_context_block = self._format_file_context(original_files, diffs, remaining_budget)
        else:
            file_context_block = "## Additional File Context\n[OMITTED due to context window limits - Focus on Diffs]"
            self.logger.warning("Historical context fully omitted due to size limits.")

        # 4. Assemble Final Prompt
        prompt_parts = [
            system_role,
            reqs_block,
            tech_block,
            diffs_block,
            file_context_block,
            schema_block
        ]
        
        full_prompt = "\n\n".join(prompt_parts)
        self.logger.info(f"Generated prompt with length: {len(full_prompt)} characters")
        return full_prompt

    def _get_system_role(self) -> str:
        return (
            "You are a Senior Software Architect & Security Expert reviewing code changes.\n"
            "Your goal is to identify bugs, security vulnerabilities, design flaws, and code style issues.\n"
            "Focus processes primarily on the logic within the PROVIDED diffs/code changes. Use the historical context only for reference."
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
            
            # Use new_content if available (full context of the changed file is better than just diff), 
            # but user specifically asked to prioritize "updated_code (Diffs)".
            # Actually, FileChangesDTO.new_content is the FULL updated content.
            # Using the DIFF (patch) is usually more token-efficient for "what changed", 
            # whereas new_content is better for "how it works now".
            # Given the prompt structure "Code Changes (Diffs)", listing the Diff patch is standard.
            # However, providing the FULL new content for the modified files is arguably "absolute priority" for a good review.
            # But adhering to the existing structure and user's instruction "diffs", we stick to diff_content.
            # We can append a snippet of new_content if diff is clean? 
            # Let's stick to the existing behavior but make sure we don't accidentally drop it.
            
            content_to_show = diff.diff_content
            if not content_to_show and diff.new_content:
                # If no diff (e.g. new file), show content
                content_to_show = diff.new_content
            
            parts.append(f"Diff/Content:\n{content_to_show}\n" + "-"*40)
        return "\n".join(parts)

    def _format_file_context(self, files: List[FileContentDTO], diffs: List[FileChangesDTO], budget: int) -> str:
        parts = ["## Additional File Context"]
        current_size = len(parts[0])
        
        changed_paths = {d.file_path for d in diffs}
        if diffs:
             for d in diffs:
                 if d.old_path:
                     changed_paths.add(d.old_path)

        truncated = False

        for file in files:
            if file.path in changed_paths:
                continue
            
            content = file.content or ""
            # Internal optimization: Cap single historical files to avoid one large file eating the budget
            if len(content) > 3000:
                content = content[:3000] + "\n[...Content Truncated...]"
            
            # Estimate size of this entry
            entry_str = f"File: {file.path}\nContent:\n{content}\n" + "-"*40
            entry_len = len(entry_str)
            
            if current_size + entry_len < budget:
                parts.append(entry_str)
                current_size += entry_len
            else:
                truncated = True
                break
        
        if truncated:
            parts.append("\n[...Remaining repository files omitted to fit context window...]")
        
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
