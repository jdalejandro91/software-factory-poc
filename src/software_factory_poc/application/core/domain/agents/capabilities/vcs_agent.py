from dataclasses import dataclass, field
from typing import Optional, List
from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.vcs_gateway import VcsGateway
from software_factory_poc.application.core.ports.gateways.dtos import FileContent

@dataclass
class VcsAgent(BaseAgent):
    """
    Agent responsible for Version Control System interactions.
    """
    gateway: VcsGateway
    project_id: Optional[int] = field(default=None, init=False)
    branch_name: Optional[str] = field(default=None, init=False)

    def branch_exists(self, repo_url: str, branch_name: str) -> Optional[str]:
        project_identifier = repo_url or "unknown/repo"
        # Cache project_id for later use in this session
        self.project_id = self.gateway.resolve_project_id(project_identifier)
        
        if self.gateway.branch_exists(self.project_id, branch_name):
            # Construct URL manually for robustness
            base_repo = repo_url.replace(".git", "").rstrip("/")
            # Initial simple heuristic for GitLab vs others
            separator = "/-/tree/" if "gitlab" in base_repo else "/tree/"
            return f"{base_repo}{separator}{branch_name}"
            
        return None

    def prepare_workspace(self, repo_url: str, branch_name: str) -> None:
        self.branch_name = branch_name
        project_identifier = repo_url or "unknown/repo"
        if not self.project_id:
             self.project_id = self.gateway.resolve_project_id(project_identifier)
        
        self.gateway.create_branch(self.project_id, branch_name)

    def publish_changes(self, files: List[FileContent], message: str) -> str:
        # 1. Transform to dict {path: content}
        files_map = {f.path: f.content for f in files}
        
        # 2. Commit Files
        # Ensure we have project_id and branch_name set (prepare_workspace should have been called)
        if not self.project_id or not self.branch_name:
             raise ValueError("Workspace not prepared. project_id or branch_name missing.")

        self.gateway.commit_files(self.project_id, self.branch_name, files_map, f"feat: {message}")
        
        # 3. Create Merge Request
        mr_result = self.gateway.create_merge_request(
            project_id=self.project_id,
            source_branch=self.branch_name,
            target_branch="main",
            title=message,
            description=f"Automated scaffolding.\n\n{message}"
        )
        
        # 4. Return URL
        return mr_result.get("web_url", "URL_NOT_FOUND")
