from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskDescription(BaseModel):
    """
    Value Object representing the description of a Task.
    Separates human-written content from machine-generated automation metadata.
    """
    model_config = ConfigDict(frozen=True)

    human_text: str = Field(..., description="The description text written by a human user.")
    raw_content: str = Field(default="", description="The original raw content string.")
    code_review_params: Optional[Dict[str, Any]] = Field(default=None, description="Structured metadata for automation output.")
    scaffolding_params: Optional[Dict[str, Any]] = Field(default=None, description="Parsed parameters for scaffolding input.")

    def has_metadata(self) -> bool:
        """Checks if the description contains automation metadata."""
        return self.code_review_params is not None and len(self.code_review_params) > 0

    def has_scaffolding_params(self) -> bool:
        """Checks if the description contains scaffolding parameters."""
        return self.scaffolding_params is not None and len(self.scaffolding_params) > 0


class Task(BaseModel):
    """
    Domain Entity representing a Task in the issue tracker.
    """
    id: str = Field(..., description="Unique identifier of the task (e.g., KAN-6)")
    project_id: str = Field(..., description="Project Key or ID (e.g. KAN)")
    summary: str = Field(..., description="Summary or title of the task")
    status: str = Field(..., description="Current status of the task")
    description: TaskDescription = Field(..., description="Rich description object")
    reporter_email: Optional[str] = Field(default=None, description="Email of the reporter/creator")

    def update_metadata(self, context: Dict[str, Any]) -> "Task":
        """
        Creates a new Task instance with updated automation metadata,
        preserving the original human text and other attributes.
        Implements immutability.
        """
        new_description = TaskDescription(
            human_text=self.description.human_text,
            raw_content=self.description.raw_content,
            scaffolding_params=self.description.scaffolding_params,
            code_review_params=context
        )
        
        return self.model_copy(update={"description": new_description})
