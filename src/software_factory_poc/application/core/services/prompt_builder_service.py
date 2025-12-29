class PromptBuilderService:
    def build_prompt(self, instruction: str, knowledge_context: str) -> str:
        """Build the final prompt combining instruction and knowledge."""
        return self._format_prompt(instruction, knowledge_context)

    def _format_prompt(self, instruction: str, knowledge_context: str) -> str:
        return (
            f"ACT AS: Senior Software Architect & Tech Lead.\n\n"
            f"MISSION: Create a clean 'Skeleton Scaffolding' for a new software project based on the requested 'template'.\n\n"
            f"INPUT CONTEXT (Architecture Pattern):\n{knowledge_context}\n\n"
            f"USER REQUEST (Contains 'template' and 'parameters'):\n{instruction}\n\n"
            f"CRITICAL RULES FOR GENERATION:\n"
            f"1. **Analyze the 'template' field** in the User Request. Use the best standard practices and folder structures for that specific framework (e.g., NestJS modules, SpringBoot packages).\n"
            f"2. **Configuration Files (FULL CONTENT)**: You MUST generate valid, complete content for all essential project configuration files. Examples: 'package.json', 'pom.xml', 'requirements.txt', 'Dockerfile', 'tsconfig.json', '.gitignore'. The project must be installable/buildable.\n"
            f"3. **Source Code Directories (DESCRIPTIVE ONLY)**: Do NOT generate business logic implementation files (no entities, no services code). Instead, create the directory structure and place a 'README.md' file inside each architectural folder (e.g., 'src/domain/README.md') describing what should go there.\n"
            f"4. **Root README**: Generate a professional 'README.md' at the root with project name, architecture overview, and setup commands.\n"
            f"5. **Output Format**: Return ONLY a valid, raw JSON object (flat dictionary 'path': 'content'). No markdown blocks.\n\n"
            f"ONE-SHOT EXAMPLE (Expected Behavior for a NestJS request):\n"
            f"{{\n"
            f"  \"package.json\": \"{{ \\\"name\\\": \\\"demo\\\", \\\"dependencies\\\": {{ \\\"@nestjs/common\\\": \\\"^10.0.0\\\" }} }}\",\n"
            f"  \"tsconfig.json\": \"{{ \\\"compilerOptions\\\": {{ ... }} }}\",\n"
            f"  \"src/main.ts\": \"// Entry point bootstrap logic only\",\n"
            f"  \"src/modules/users/README.md\": \"# Users Module\\n\\nThis folder contains the User domain logic, controllers and providers.\",\n"
            f"  \"src/shared/infrastructure/README.md\": \"# Shared Infrastructure\\n\\nCommon adapters and database configuration.\",\n"
            f"  \"README.md\": \"# Project Title\\n\\n## Architecture\\nModular Monolith...\"\n"
            f"}}"
        )
