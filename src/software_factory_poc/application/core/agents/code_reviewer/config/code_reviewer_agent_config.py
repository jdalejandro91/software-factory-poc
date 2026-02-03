from dataclasses import dataclass

@dataclass
class CodeReviewerAgentConfig:
    """Configuration for the Code Reviewer Agent."""
    api_key: str
    model: str
    llm_model_priority: list[str]
