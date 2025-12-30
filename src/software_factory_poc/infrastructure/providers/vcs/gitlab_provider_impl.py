import urllib.parse
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from software_factory_poc.application.core.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import (
    GitLabHttpClient,
)
from software_factory_poc.infrastructure.providers.vcs.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import (
    GitLabBranchService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import (
    GitLabCommitService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_mr_service import (
    GitLabMergeRequestService,
)
from software_factory_poc.application.core.domain.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import VcsProviderType

logger = LoggerFactoryService.build_logger(__name__)


class GitLabProviderImpl(GitLabProvider):
    def __init__(
        self, 
        http_client: GitLabHttpClient,
        payload_builder: GitLabPayloadBuilderService
    ):
        self.client = http_client
        self.payload_builder = payload_builder
        self._logger = logger
        
        # Initialize internal services
        self.branch_service = GitLabBranchService(http_client)
        self.commit_service = GitLabCommitService(http_client, payload_builder)
        self.mr_service = GitLabMergeRequestService(http_client)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def resolve_project_id(self, project_path: str) -> int:
        """
        Resolves a project path (group/project) to an numeric ID.
        """
        self._logger.info(f"Resolving project ID for path: {project_path}")
        try:
            encoded_path = urllib.parse.quote(project_path, safe="")
            response = self.client.get(f"api/v4/projects/{encoded_path}")
            
            if response.status_code == 404:
                # 404 is technically not a connection error, so maybe we don't retry? 
                # But tenacity reraises everything by default.
                # We map it to a clear error.
                raise ValueError(f"GitLab project path not found: {project_path}")
                
            response.raise_for_status()
            return response.json()["id"]
        except Exception as e:
            self._handle_error(e, f"resolve_project_id({project_path})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_branch(self, project_id: int, branch_name: str) -> dict[str, Any] | None:
        self._logger.info(f"Getting branch: {branch_name} (Project: {project_id})")
        try:
            return self.branch_service.get_branch(project_id, branch_name)
        except Exception as e:
            self._handle_error(e, f"get_branch({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def branch_exists(self, project_id: int, branch_name: str) -> bool:
        # Check existence often returns boolean, maybe logging is verbose here?
        # Keeping info level as requested.
        self._logger.info(f"Checking if branch exists: {branch_name} (Project: {project_id})")
        try:
            return self.branch_service.branch_exists(project_id, branch_name)
        except Exception as e:
            self._handle_error(e, f"branch_exists({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> dict[str, Any]:
        self._logger.info(f"Creating branch: {branch_name} from {ref} (Project: {project_id})")
        try:
            return self.branch_service.create_branch(project_id, branch_name, ref)
        except Exception as e:
            self._handle_error(e, f"create_branch({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def file_exists(self, project_id: int, file_path: str, ref: str) -> bool:
        self._logger.info(f"Checking if file exists: {file_path} on {ref} (Project: {project_id})")
        try:
            return self.commit_service.file_exists(project_id, file_path, ref)
        except Exception as e:
            self._handle_error(e, f"file_exists({file_path})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def commit_files(
        self, 
        project_id: int, 
        branch_name: str, 
        files_map: dict[str, str],
        commit_message: str
    ) -> dict[str, Any]:
        self._logger.info(f"Committing {len(files_map)} files to {branch_name} (Project: {project_id})")
        try:
            return self.commit_service.commit_files(project_id, branch_name, files_map, commit_message)
        except Exception as e:
            self._handle_error(e, f"commit_files(count={len(files_map)})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_merge_request(self, project_id: int, source_branch: str, target_branch: str, title: str, description: str | None = None) -> dict[str, Any]:
        self._logger.info(f"Creating MR: {source_branch} -> {target_branch} (Project: {project_id})")
        try:
            return self.mr_service.create_merge_request(project_id, source_branch, target_branch, title, description)
        except Exception as e:
            self._handle_error(e, "create_merge_request")
            raise

    def _handle_error(self, error: Exception, context: str) -> None:
        """Centralized error handling and logging."""
        # Clean existing logging (if any internal service logged it, this might be duplicate but ensures Error level)
        self._logger.error(f"Error in GitLabProviderImpl [{context}]: {str(error)}", exc_info=True)
        
        if isinstance(error, ProviderError):
            # Already mapped
            return
            
        # Map generic exceptions
        # Note: requests.HTTPError might be raised by services. 
        # We can inspect status codes if we import requests, or rely on string checking as simplest generic way without tight coupling.
        msg = str(error)
        retryable = False
        if "500" in msg or "502" in msg or "503" in msg or "504" in msg:
            retryable = True
        elif "Connection" in msg or "Timeout" in msg:
             retryable = True
             
        raise ProviderError(
            provider=VcsProviderType.GITLAB,
            message=f"GitLab operation failed: {error}",
            retryable=retryable
        ) from error
