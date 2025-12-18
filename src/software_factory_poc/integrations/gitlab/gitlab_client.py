from typing import Any, Dict
import urllib.parse
import httpx
from pydantic import SecretStr

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.integrations.gitlab.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class GitLabClient:
    def __init__(
        self, 
        settings: Settings,
        payload_builder: GitLabPayloadBuilderService
    ):
        self.settings = settings
        self.payload_builder = payload_builder
        self.base_url = settings.gitlab_base_url.rstrip("/")
        self._validate_config()

    def _validate_config(self):
        self.settings.validate_gitlab_credentials()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        token = self.settings.gitlab_token.get_secret_value() if self.settings.gitlab_token else ""
        
        # Simple heuristic: user requested support for Bearer if configured.
        # Since we don't have a distinct config flag for AuthMode in this PoC iteration,
        # we'll use PRIVATE-TOKEN by default as it's the standard for PATs.
        headers["PRIVATE-TOKEN"] = token
        return headers

    def resolve_project_id(self, project_path: str) -> int:
        """
        Resolves a project path (group/project) to an numeric ID.
        """
        encoded_path = urllib.parse.quote(project_path, safe="")
        url = f"{self.base_url}/api/v4/projects/{encoded_path}"
        logger.info(f"Resolving project ID for path: {project_path}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 404:
                raise ValueError(f"GitLab project path not found: {project_path}")
            response.raise_for_status()
            data = response.json()
            return data["id"]

    def create_branch(self, project_id: int, branch_name: str, ref: str) -> Dict[str, Any]:
        """
        Creates a new branch from a reference (e.g. main).
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/branches"
        logger.info(f"Creating GitLab branch '{branch_name}' in project {project_id} from '{ref}'")
        
        payload = {
            "branch": branch_name,
            "ref": ref
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()

    def commit_files(
        self, 
        project_id: int, 
        branch_name: str, 
        files_map: Dict[str, str], 
        commit_message: str
    ) -> Dict[str, Any]:
        """
        Commits files to a branch.
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
        logger.info(f"Committing {len(files_map)} files to branch '{branch_name}' in project {project_id}")
        
        payload = self.payload_builder.build_commit_payload(
            files_map=files_map,
            branch_name=branch_name,
            message=commit_message
        )
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=20.0) # Larger timeout for commits
            response.raise_for_status()
            return response.json()

    def create_merge_request(
        self, 
        project_id: int, 
        source_branch: str, 
        target_branch: str, 
        title: str, 
        description: str
    ) -> Dict[str, Any]:
        """
        Creates a Merge Request.
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests"
        logger.info(f"Creating MR from '{source_branch}' to '{target_branch}' in project {project_id}")
        
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "remove_source_branch": True
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
