class PromptBuilderService:
    def build_prompt(self, instruction: str, knowledge_context: str) -> str:
        """Build the final prompt combining instruction and knowledge."""
        return self._format_prompt(instruction, knowledge_context)

    def _format_prompt(self, instruction: str, knowledge_context: str) -> str:
        return (
            f"CONTEXT:\n{knowledge_context}\n\n"
            f"INSTRUCTION:\n{instruction}\n\n"
            "Generate the code structure based on the above."
        )
