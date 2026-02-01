from datetime import datetime

import yaml
from pydantic import BaseModel, Field, ConfigDict


class AutomationContextDTO(BaseModel):
    """
    Standardizes the automation state payload passed between Scaffolding and Code Review agents.
    Acts as the schema for the YAML block injected into Jira.
    """
    model_config = ConfigDict(frozen=True)

    gitlab_project_id: str = Field(..., description="GitLab Project ID (as string for compatibility)")
    source_branch_name: str = Field(..., description="Name of the source branch created")
    review_request_url: str = Field(..., description="URL of the Merge Request")
    generated_at: str = Field(..., description="ISO timestamp of generation")

    def to_yaml_block(self) -> str:
        """
        Formats the context as a machine-readable YAML block for Jira descriptions.
        """
        data = {
            "automation_result": {
                "gitlab_project_id": self.gitlab_project_id,
                "source_branch_name": self.source_branch_name,
                "review_request_url": self.review_request_url,
                "generated_at": self.generated_at
            }
        }
        
        # Helper to ensure clean YAML dump
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False).strip()
        
        return (
            f"# --- AUTOMATION STATE (Machine Readable) ---\n"
            f"```yaml\n"
            f"{yaml_str}\n"
            f"```"
        )

    @classmethod
    def from_values(cls, project_id: str, branch: str, mr_url: str) -> "AutomationContextDTO":
        """Factory method for creating context with current timestamp."""
        return cls(
            gitlab_project_id=str(project_id),
            source_branch_name=branch,
            review_request_url=mr_url,
            generated_at=datetime.utcnow().isoformat()
        )
