from dataclasses import dataclass

@dataclass
class ContractParseError(Exception):
    """Raised when the LLM response cannot be parsed into the expected contract."""
    message: str
    original_text: str

    @property
    def safe_snippet(self) -> str:
        """Returns a truncated/safe version of the original text."""
        if not self.original_text:
            return ""
        return self.original_text[:200] + "..." if len(self.original_text) > 200 else self.original_text

    def __str__(self):
        return f"ContractParseError: {self.message} | Snippet: {self.safe_snippet}"
