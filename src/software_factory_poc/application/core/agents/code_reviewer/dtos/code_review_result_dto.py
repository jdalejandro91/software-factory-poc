from typing import List, Optional

from pydantic import BaseModel, Field

from software_factory_poc.application.core.agents.code_reviewer.dtos.review_enums import (
    ReviewSeverity,
    ReviewVerdict,
)


class ReviewCommentDTO(BaseModel):
    """
    Represents a specific review comment on a file.
    """
    model_config = {"frozen": True}

    file_path: str = Field(..., description="Path of the file being reviewed.")
    line_number: Optional[int] = Field(
        None, 
        description="Line number in the NEW version of the file. None for global file comments."
    )
    severity: ReviewSeverity
    comment_body: str = Field(..., description="Detailed explanation of the finding.")
    suggestion: Optional[str] = Field(
        None, 
        description="The suggested code block replacement *only*. Do not include markdown backticks."
    )


class CodeReviewResultDTO(BaseModel):
    """
    Aggregates the entire result of a code review session.
    """
    model_config = {"frozen": True}

    summary: str = Field(..., description="Markdown executive summary of the review.")
    verdict: ReviewVerdict
    comments: List[ReviewCommentDTO] = Field(..., description="List of detailed findings.")
