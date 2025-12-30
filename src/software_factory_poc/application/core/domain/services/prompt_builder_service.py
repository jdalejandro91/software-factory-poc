class PromptBuilderService:
    @staticmethod
    def build_system_prompt(technology_stack: str) -> str:
        """
        Builds the system prompt/persona.
        """
        return (
            f"ACT AS: Senior Software Architect & Tech Lead.\n"
            f"MISSION: Create a clean 'Skeleton Scaffolding' for a new software project based on the requested '{technology_stack}'.\n"
            f"You are an expert in {technology_stack} ecosystem."
        )

    @staticmethod
    def build_user_prompt(request_instruction: str, context: str) -> str:
        """
        Builds the user prompt with context and instructions.
        """
        return PromptBuilderService._format_prompt_body(request_instruction, context)

    @staticmethod
    def _format_prompt_body(instruction: str, knowledge_context: str) -> str:
        parts = [
            f"INPUT CONTEXT (Architecture Pattern):\n{knowledge_context}\n\n",
            f"USER REQUEST (Contains 'technology_stack' and 'parameters'):\n{instruction}\n\n",
            "CRITICAL RULES FOR GENERATION:\n",
            "1. **Analyze the 'technology_stack' field** in the User Request. Use the best standard practices and folder structures for that specific framework (e.g., NestJS modules, SpringBoot packages).\n",
            "2. **Configuration Files (FULL CONTENT)**: You MUST generate valid, complete content for all essential project configuration files. Examples: 'package.json', 'pom.xml', 'requirements.txt', 'Dockerfile', 'tsconfig.json', '.gitignore'. The project must be installable/buildable.\n",
            "3. **Source Code Directories (DESCRIPTIVE ONLY)**: Do NOT generate business logic implementation files (no entities, no services code). Instead, create the directory structure and place a 'README.md' file inside each architectural folder (e.g., 'src/domain/README.md') describing what should go there.\n",
            "4. **Root README**: Generate a professional 'README.md' at the root with project name, architecture overview, and setup commands.\n",
            "5. **Output Format**: You must use strict code blocks with a special header for each file. Do NOT return a single JSON object. Use the format:\n",
            "<<<FILE:path/to/file>>>\n",
            "file content here...\n",
            "<<<END>>>\n\n",
            "ONE-SHOT EXAMPLE:\n",
            "<<<FILE:src/main.py>>>\n",
            "print('Hello')\n",
            "<<<END>>>\n",
            "<<<FILE:README.md>>>\n",
            "# Demo\n",
            "<<<END>>>"
        ]
        return "".join(parts)
