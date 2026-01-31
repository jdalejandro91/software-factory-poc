import urllib.parse
from typing import Any, Optional, List
from typing import Any, Optional, List
from software_factory_poc.application.core.agents.common.dtos.change_type import ChangeType
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO

from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.application.core.agents.common.exceptions.provider_error import ProviderError
from software_factory_poc.application.core.agents.vcs.config.vcs_provider_type import VcsProviderType
from software_factory_poc.application.core.agents.vcs.dtos.vcs_dtos import BranchDTO, CommitResultDTO, MergeRequestDTO
from software_factory_poc.application.core.agents.vcs.ports.vcs_gateway import VcsGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import (
    GitLabHttpClient,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import (
    GitLabBranchService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import (
    GitLabCommitService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_mr_service import (
    GitLabMrService,
)

logger = LoggerFactoryService.build_logger(__name__)


class GitLabProviderImpl(VcsGateway):
    def __init__(
            self,
            branch_service: GitLabBranchService,
            commit_service: GitLabCommitService,
            mr_service: GitLabMrService,
            http_client: GitLabHttpClient
    ):
        self._logger = logger
        self.client = http_client
        self.branch_service = branch_service
        self.commit_service = commit_service
        self.mr_service = mr_service

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def resolve_project_id(self, repo_url: str) -> int:
        if not repo_url or not repo_url.strip():
            raise ValueError("GitLabProvider: Cannot resolve project ID. 'repo_url' provided is empty.")

        project_path = repo_url
        if "://" in project_path:
            try:
                parsed = urllib.parse.urlparse(project_path)
                project_path = parsed.path.lstrip("/")
                if project_path.endswith(".git"):
                    project_path = project_path[:-4]
            except Exception:
                pass

        if not project_path or not project_path.strip():
            raise ValueError(f"GitLabProvider: Parsed project path is empty from url '{repo_url}'")

        self._logger.info(f"Resolving project ID for path: {project_path}")
        try:
            encoded_path = urllib.parse.quote(project_path, safe="")
            response = self.client.get(f"api/v4/projects/{encoded_path}")

            if response.status_code == 404:
                raise ValueError(f"GitLab project path not found: {project_path}")

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                raise ProviderError(
                    provider=VcsProviderType.GITLAB,
                    message=f"GitLab API returned a list instead of a project object. Check if path '{project_path}' is ambiguous.",
                    retryable=False
                )

            return data["id"]
        except Exception as e:
            self._handle_error(e, f"resolve_project_id({project_path})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_branch(self, project_id: int, branch_name: str) -> Optional[dict[str, Any]]:
        self._logger.info(f"Getting branch: {branch_name} (Project: {project_id})")
        try:
            return self.branch_service.get_branch(project_id, branch_name)
        except Exception as e:
            self._handle_error(e, f"get_branch({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def branch_exists(self, project_id: int, branch_name: str) -> bool:
        self._logger.info(f"Checking if branch exists: {branch_name} (Project: {project_id})")
        try:
            return self.branch_service.branch_exists(project_id, branch_name)
        except Exception as e:
            self._handle_error(e, f"branch_exists({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> BranchDTO:
        self._logger.info(f"Creating branch: {branch_name} from {ref} (Project: {project_id})")
        try:
            result = self.branch_service.create_branch(project_id, branch_name, ref)
            return BranchDTO(
                name=result.get("name", branch_name),
                web_url=result.get("web_url", "")
            )
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
            commit_message: str,
            force_create: bool = False
    ) -> CommitResultDTO:
        self._logger.info(f"Committing {len(files_map)} files to {branch_name} (Project: {project_id})")
        try:
            result = self.commit_service.commit_files(project_id, branch_name, files_map, commit_message, force_create)
            return CommitResultDTO(
                id=result.get("id", "unknown"),
                web_url=result.get("web_url", "")
            )
        except Exception as e:
            self._handle_error(e, f"commit_files(count={len(files_map)})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_merge_request(self, project_id: int, source_branch: str, target_branch: str, title: str,
                             description: Optional[str] = None) -> MergeRequestDTO:
        self._logger.info(f"Creating MR: {source_branch} -> {target_branch} (Project: {project_id})")
        try:
            result = self.mr_service.create_merge_request(project_id, source_branch, target_branch, title,
                                                          description or "")

            # FIX: Validate Web URL availability
            web_url = result.get("web_url")
            if not web_url:
                self._logger.error(f"GitLab API returned MR without 'web_url'. Full response keys: {result.keys()}")
                # Fallback to avoid broken links if possible, or raise
                # Raising ensures we spot the error instead of sending a dead link to Jira
                raise ValueError("GitLab MR created but 'web_url' is missing in response.")

            return MergeRequestDTO(
                id=str(result.get("iid", result.get("id", "0"))),
                web_url=web_url,
                state=result.get("state", "opened")
            )
        except Exception as e:
            self._handle_error(e, "create_merge_request")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_repository_files(self, project_id: int, branch_name: str) -> List[FileContentDTO]:
        self._logger.info(f"Fetching file list for project {project_id} on branch {branch_name}...")
        
        all_files = []
        page = 1
        per_page = 100
        
        try:
            while True:
                response = self.client.get(
                    f"api/v4/projects/{project_id}/repository/tree",
                    params={
                        "ref": branch_name,
                        "recursive": True,
                        "per_page": per_page,
                        "page": page
                    }
                )
                
                if response.status_code == 404:
                     raise ProviderError(
                        provider=VcsProviderType.GITLAB,
                        message=f"Branch '{branch_name}' not found for project {project_id}",
                        retryable=False
                    )
                
                response.raise_for_status()
                items = response.json()
                
                if not items:
                    break
                
                all_files.extend(items)
                page += 1
                
            # Filter and Download
            result_dtos = []
            binary_extensions = {
                '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf', 
                '.zip', '.tar', '.gz', '.pyc', '.exe', '.dll', '.so', '.bin', '.lock'
            }
            
            filtered_files = []
            for item in all_files:
                if item['type'] != 'blob':
                    continue
                
                path = item['path']
                ext = ""
                if "." in path:
                    ext = "." + path.split(".")[-1].lower()
                
                if ext in binary_extensions:
                    continue
                    
                filtered_files.append(path)

            self._logger.info(f"Found {len(all_files)} items. Downloading {len(filtered_files)} text files...")

            for file_path in filtered_files:
                try:
                    encoded_path = urllib.parse.quote(file_path, safe="")
                    # Get raw content
                    resp = self.client.get(
                        f"api/v4/projects/{project_id}/repository/files/{encoded_path}/raw",
                        params={"ref": branch_name}
                    )
                    resp.raise_for_status()
                    
                    content = resp.text
                    result_dtos.append(FileContentDTO(path=file_path, content=content))
                    
                except Exception as e:
                     self._logger.warning(f"Failed to download/decode {file_path}: {e}")
            
            self._logger.info(f"Downloaded {len(result_dtos)} files.")
            return result_dtos

        except Exception as e:
            self._handle_error(e, f"get_repository_files({branch_name})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_merge_request_diffs(self, project_id: int, mr_id: str) -> List[FileChangesDTO]:
        self._logger.info(f"Fetching diffs for MR {mr_id} in project {project_id}")
        try:
            raw_changes = self.mr_service.get_mr_changes(project_id, mr_id)
            result_dtos = []
            
            for change in raw_changes:
                new_path = change.get("new_path")
                old_path = change.get("old_path")
                new_file = change.get("new_file", False)
                deleted_file = change.get("deleted_file", False)
                renamed_file = change.get("renamed_file", False)
                diff_content = change.get("diff", "")
                
                # Derive ChangeType
                change_type = ChangeType.MODIFIED
                if new_file:
                    change_type = ChangeType.ADDED
                elif deleted_file:
                    change_type = ChangeType.DELETED
                elif renamed_file:
                    change_type = ChangeType.RENAMED
                    
                # Calculate stats
                additions = 0
                deletions = 0
                if diff_content:
                    lines = diff_content.split('\n')
                    for line in lines:
                        if line.startswith('+') and not line.startswith('+++'):
                            additions += 1
                        elif line.startswith('-') and not line.startswith('---'):
                            deletions += 1
                            
                dto = FileChangesDTO(
                    file_path=new_path,
                    old_path=old_path,
                    change_type=change_type,
                    diff_content=diff_content,
                    additions=additions,
                    deletions=deletions,
                    is_binary=False # GitLab usually handles binary diffs separately/empty, defaulting False for safety
                )
                result_dtos.append(dto)
                
            return result_dtos
            
        except Exception as e:
            self._handle_error(e, f"get_merge_request_diffs({mr_id})")
            raise

    def _handle_error(self, error: Exception, context: str) -> None:
        self._logger.error(f"Error in GitLabProviderImpl [{context}]: {str(error)}", exc_info=True)
        if isinstance(error, ProviderError):
            return
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