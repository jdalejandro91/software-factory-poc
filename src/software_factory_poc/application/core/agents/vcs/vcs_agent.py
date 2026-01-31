from dataclasses import dataclass
from typing import Optional

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.vcs.dtos.vcs_dtos import MergeRequestDTO, CommitResultDTO, BranchDTO
from software_factory_poc.application.core.agents.vcs.ports.vcs_gateway import VcsGateway


@dataclass
class VcsAgent(BaseAgent):
    """
    Agent responsible for Version Control System interactions.
    Exposes atomic operations mapping 1:1 to the VCS Gateway.
    """
    gateway: VcsGateway

    def resolve_project_id(self, repo_url: str) -> int:
        """Resolves the project ID for a given repository URL."""
        return self.gateway.resolve_project_id(repo_url)

    def validate_branch(self, project_id: int, branch_name: str, repo_url_hint: str = "") -> Optional[str]:
        """Checks if a branch exists and returns its URL if it does."""
        if not self.gateway.branch_exists(project_id, branch_name):
            return None
            
        # Construct URL manually for robustness
        # Strip .git suffix if present
        base_repo = repo_url_hint
        if base_repo.endswith(".git"):
            base_repo = base_repo[:-4]
        base_repo = base_repo.rstrip("/")
        
        # Determine separator based on provider hint in URL
        separator = "/-/tree/" if "gitlab" in base_repo else "/tree/"
        return f"{base_repo}{separator}{branch_name}"

    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> BranchDTO:
        """Creates a new branch from main."""
        return self.gateway.create_branch(project_id, branch_name, ref)

    def commit_files(self, project_id: int, branch_name: str, files_map: dict[str, str], message: str, force_create: bool = False) -> CommitResultDTO:
        """Commits files to the specified branch."""
        return self.gateway.commit_files(project_id, branch_name, files_map, message, force_create)

    def create_merge_request(self, project_id: int, source_branch: str, title: str, description: str, target_branch: str = "main") -> MergeRequestDTO:
        """Creates a merge request and returns the DTO."""
        return self.gateway.create_merge_request(
            project_id=project_id,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            description=description
        )
