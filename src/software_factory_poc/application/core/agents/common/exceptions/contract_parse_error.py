from dataclasses import dataclass

@dataclass
class ContractParseError(Exception):
    """Raised when the LLM response cannot be parsed into the expected contract."""
    message: str
    original_text: str

    def __str__(self):
        return f"ContractParseError: {self.message}"
