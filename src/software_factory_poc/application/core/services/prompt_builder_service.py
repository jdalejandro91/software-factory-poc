class PromptBuilderService:
    def build_prompt(self, instruction: str, knowledge_context: str) -> str:
        """Build the final prompt combining instruction and knowledge."""
        return self._format_prompt(instruction, knowledge_context)

    def _format_prompt(self, instruction: str, knowledge_context: str) -> str:
        return (
            f"ACT AS: Senior Software Architect & Code Generator.\n\n"
            f"MISSION: Generate the full directory structure and file contents for a software project based on the following requirements and architectural knowledge.\n\n"
            f"INPUT CONTEXT:\n{knowledge_context}\n\n"
            f"USER REQUEST:\n{instruction}\n\n"
            f"OUTPUT RULES (STRICT):\n"
            f"1. You must return ONLY a valid JSON object. No conversational text, no markdown blocks, no preamble.\n"
            f"2. The JSON format must be a flat dictionary where:\n"
            f"   - Keys are the relative file paths (e.g., \"src/domain/user.py\").\n"
            f"   - Values are the full content of the file (source code).\n"
            f"3. Do NOT create empty directories. If a directory is architecturally necessary but empty of code, create a \"README.md\" inside it explaining its purpose.\n"
            f"4. For Python projects, ensure \"__init__.py\" exists in packages.\n"
            f"5. Code must be production-ready, following Clean Architecture and DDD.\n\n"
            f"EXAMPLE OUTPUT:\n"
            f"{{\n"
            f"  \"src/main.py\": \"print('hello')\",\n"
            f"  \"src/domain/__init__.py\": \"\",\n"
            f"  \"src/domain/models.py\": \"class User:...\",\n"
            f"  \"docs/architecture/README.md\": \"This folder contains...\"\n"
            f"}}"
        )
