from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class GitLabTargetModel(BaseModel):
    project_id: int | None = Field(None, description="Target GitLab project ID")
    project_path: str | None = Field(None, description="Target GitLab project path (e.g. group/project)", alias="gitlab_project_path")
    target_base_branch: str | None = Field(None, description="Base branch to branch off from (e.g. main)")
    branch_slug: str | None = Field(None, description="Branch slug for the feature branch")

    @field_validator("project_id")
    def validate_project_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("project_id must be positive")
        return v
    
    @model_validator(mode="after")
    def validate_project_identifier(self) -> "GitLabTargetModel":
        if not self.project_id and not self.project_path:
            raise ValueError("Must provide either 'project_id' or 'project_path' (or 'gitlab_project_path').")
        return self


class JiraTargetModel(BaseModel):
    comment_visibility: str | None = Field("public", description="e.g. 'public' or 'internal'")


class ScaffoldingContractModel(BaseModel):
    contract_version: str = Field(..., description="Version of the contract schema, e.g. '1.0'", alias="version")
    technology_stack: str = Field(..., description="The tech stack to use, e.g., 'NodeJS', 'Python', 'Java SpringBoot'")
    
    # Optional logic: Derived from parameters.service_name if not strict
    service_slug: str | None = Field(None, description="Slug for the new service, used in branch naming")
    
    gitlab: GitLabTargetModel = Field(..., alias="target")
    jira: JiraTargetModel | None = Field(default_factory=JiraTargetModel)
    
    vars: dict[str, Any] = Field(default_factory=dict, description="Variables for template rendering", alias="parameters")

    @field_validator("contract_version")
    def validate_version(cls, v: str) -> str:
        # Allow "1" or "1.0"
        if v not in ("1", "1.0"):
            raise ValueError("Only contract_version '1' or '1.0' is supported")
        return v

    @field_validator("technology_stack")
    def validate_technology_stack(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("technology_stack cannot be empty")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def populate_service_slug(cls, data: Any) -> Any:
        # If input is dict
        if isinstance(data, dict):
            # Check if service_slug is present
            if not data.get("service_slug"):
                # Try to get from parameters/vars
                params = data.get("parameters") or data.get("vars") or {}
                if isinstance(params, dict) and params.get("service_name"):
                    data["service_slug"] = params.get("service_name")
        return data

    @model_validator(mode="after")
    def validate_service_slug_exists(self) -> "ScaffoldingContractModel":
        if not self.service_slug or not self.service_slug.strip():
             raise ValueError("service_slug is required (or must be derivable from parameters.service_name)")
        return self
