from dataclasses import dataclass
from typing import Optional, List

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import ReviewCommentDTO
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.vcs.dtos.vcs_dtos import MergeRequestDTO, CommitResultDTO, BranchDTO
from software_factory_poc.application.core.agents.vcs.ports.vcs_gateway import VcsGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


@dataclass
class VcsAgent(BaseAgent):
    """
    Agent responsible for Version Control System interactions.
    Exposes atomic operations mapping 1:1 to the VCS Gateway.
    """
    gateway: VcsGateway

    def __post_init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)
        self.logger.info("VcsAgent initialized")

    def resolve_project_id(self, repo_url: str) -> int:
        """Resolves the project ID for a given repository URL."""
        return self.gateway.resolve_project_id(repo_url)

    def validate_branch(self, project_id: int, branch_name: str) -> Optional[str]:
        """Checks if a branch exists and returns its URL if it does."""
        dto = self.gateway.get_branch_details(project_id, branch_name)
        if dto:
            return dto.web_url
        return None

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

    def get_code_context(self, project_id: int, branch: str, max_files: int = 50, max_file_size_kb: int = 100) -> List[FileContentDTO]:
        """Retrieves code context (files) from the repository with safety limits."""
        self.logger.info(f"Fetching code context from branch '{branch}' for project {project_id}")
        return self.gateway.get_repository_files(project_id, branch, max_files, max_file_size_kb)

    def get_mr_changes(self, project_id: int, mr_id: str) -> List[FileChangesDTO]:
        """Retrieves file changes for a specific Merge Request."""
        self.logger.info(f"Fetching diffs for MR {mr_id} in project {project_id}")
        return self.gateway.get_merge_request_diffs(project_id, mr_id)

    def submit_review(self, project_id: int, mr_id: str, comments: List[ReviewCommentDTO]) -> None:
        """Submits review comments to a Merge Request."""
        self.logger.info(f"Submitting {len(comments)} review comments to MR {mr_id} in project {project_id}")
        self.gateway.post_review_comments(project_id, mr_id, comments)

    def validate_mr(self, project_id: int, mr_id: str) -> bool:
        """Validates if a Merge Request exists."""
        self.logger.info(f"Validating existence of MR {mr_id} in project {project_id}")
        return self.gateway.validate_mr_exists(project_id, mr_id)
