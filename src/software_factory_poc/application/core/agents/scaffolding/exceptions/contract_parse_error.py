class ContractParseError(Exception):
    """
    Raised when the LLM response cannot be parsed into the expected contract.
    """
    def __init__(self, message: str, safe_snippet: str = ""):
        self.message = message
        self.safe_snippet = safe_snippet
        super().__init__(f"{message} | Snippet: {safe_snippet}")