from dataclasses import dataclass
from typing import Optional
from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.domain.agents.vcs.ports.vcs_gateway import VcsGateway
from software_factory_poc.application.core.domain.agents.vcs.dtos.vcs_dtos import MergeRequestDTO, CommitResultDTO, BranchDTO


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

    def check_branch_exists(self, project_id: int, branch_name: str, repo_url_hint: str = "") -> Optional[str]:
        """Checks if a branch exists and returns its URL if it does."""
        if not self.gateway.branch_exists(project_id, branch_name):
            return None
            
        # Construct URL manually for robustness
        base_repo = repo_url_hint.replace(".git", "").rstrip("/")
        separator = "/-/tree/" if "gitlab" in base_repo else "/tree/"
        return f"{base_repo}{separator}{branch_name}"

    def create_branch(self, project_id: int, branch_name: str) -> BranchDTO:
        """Creates a new branch from main."""
        return self.gateway.create_branch(project_id, branch_name)

    def commit_files(self, project_id: int, branch_name: str, files_map: dict[str, str], message: str) -> CommitResultDTO:
        """Commits files to the specified branch."""
        return self.gateway.commit_files(project_id, branch_name, files_map, message)

    def create_merge_request(self, project_id: int, source_branch: str, title: str, description: str) -> MergeRequestDTO:
        """Creates a merge request and returns the DTO."""
        return self.gateway.create_merge_request(
            project_id=project_id,
            source_branch=source_branch,
            target_branch="main",
            title=title,
            description=description
        )
