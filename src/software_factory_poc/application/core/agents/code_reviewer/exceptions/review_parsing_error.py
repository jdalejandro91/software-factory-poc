class ReviewParsingError(Exception):
    """Exception raised when parsing AI review results fails."""
    
    def __init__(self, message: str, original_text: str):
        super().__init__(message)
        self.message = message
        self.original_text = original_text
