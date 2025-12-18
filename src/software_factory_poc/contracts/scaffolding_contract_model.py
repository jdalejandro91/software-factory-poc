from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class GitLabTargetModel(BaseModel):
    project_id: int = Field(..., description="Target GitLab project ID")
    target_base_branch: Optional[str] = Field(None, description="Base branch to branch off from (e.g. main)")

    @field_validator("project_id")
    def validate_project_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("project_id must be positive")
        return v


class JiraTargetModel(BaseModel):
    comment_visibility: Optional[str] = Field("public", description="e.g. 'public' or 'internal'")


class ScaffoldingContractModel(BaseModel):
    contract_version: str = Field(..., description="Version of the contract schema, e.g. '1'")
    template_id: str = Field(..., description="ID of the template to use")
    service_slug: str = Field(..., description="Slug for the new service, used in branch naming")
    
    gitlab: GitLabTargetModel
    jira: Optional[JiraTargetModel] = Field(default_factory=JiraTargetModel)
    
    vars: Dict[str, Any] = Field(default_factory=dict, description="Variables for template rendering")

    @field_validator("contract_version")
    def validate_version(cls, v: str) -> str:
        if v != "1":
            raise ValueError("Only contract_version '1' is supported")
        return v

    @field_validator("template_id")
    def validate_template_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("template_id cannot be empty")
        return v.strip()

    @field_validator("service_slug")
    def validate_service_slug(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("service_slug cannot be empty")
        return v.strip()
