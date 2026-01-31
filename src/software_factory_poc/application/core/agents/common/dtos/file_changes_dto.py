from typing import Optional

from pydantic import BaseModel, Field

from software_factory_poc.application.core.agents.common.dtos.change_type import ChangeType


class FileChangesDTO(BaseModel):
    """
    Represents changes in a single file with all necessary context for Code Review.
    """
    model_config = {"frozen": True}

    file_path: str = Field(..., description="The new path of the file. references the file's current location.")
    old_path: Optional[str] = Field(
        None, 
        description="CRITICAL: The previous path of the file if RENAMED or MODIFIED. Required by GitLab for the 'position' object in threads."
    )
    change_type: ChangeType
    diff_content: Optional[str] = Field(None, description="The raw diff/patch content.")
    is_binary: bool = Field(False, description="Flag to indicate if the file is binary.")
    additions: int = Field(0, description="Number of lines added.")
    deletions: int = Field(0, description="Number of lines deleted.")
    new_content: Optional[str] = Field(None, description="The full content of the file after changes.")

    def get_primary_path(self) -> str:
        """
        Returns the most relevant path for display or logging.
        Prefer current path, fallback to old path (e.g., if deleted and file_path is somehow missing, though file_path is required).
        """
        return self.file_path or self.old_path or "unknown_path"
