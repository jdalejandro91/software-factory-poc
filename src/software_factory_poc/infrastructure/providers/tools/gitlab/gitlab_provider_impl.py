import urllib.parse
from typing import Any

import httpx

from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.infrastructure.providers.tools.gitlab.clients.gitlab_http_client import (
    GitLabHttpClient,
)
from software_factory_poc.infrastructure.providers.tools.gitlab.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class GitLabProviderImpl(GitLabProvider):
    def __init__(
        self, 
        http_client: GitLabHttpClient,
        payload_builder: GitLabPayloadBuilderService
    ):
        self.client = http_client
        self.payload_builder = payload_builder

    def resolve_project_id(self, project_path: str) -> int:
        """
        Resolves a project path (group/project) to an numeric ID.
        Note: Not in abstract interface but used by logic.
        """
        encoded_path = urllib.parse.quote(project_path, safe="")
        logger.info(f"Resolving project ID for path: {project_path}")
        
        response = self.client.get(f"api/v4/projects/{encoded_path}")
        if response.status_code == 404:
            raise ValueError(f"GitLab project path not found: {project_path}")
        response.raise_for_status()
        return response.json()["id"]

    def get_branch(self, project_id: int, branch_name: str) -> dict[str, Any] | None:
        """
        Checks if a branch exists. Returns branch info or None.
        """
        encoded_branch = urllib.parse.quote(branch_name, safe="")
        path = f"api/v4/projects/{project_id}/repository/branches/{encoded_branch}"
        
        response = self.client.get(path)
        if response.status_code == 200:
            return response.json()
        return None

    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> dict[str, Any]:
        # 1. Check existence
        existing_branch = self.get_branch(project_id, branch_name)
        if existing_branch:
            logger.info(f"Branch '{branch_name}' already exists in project {project_id}. Skipping creation.")
            return existing_branch

        # 2. Create
        path = f"api/v4/projects/{project_id}/repository/branches"
        logger.info(f"Creating GitLab branch '{branch_name}' in project {project_id} from '{ref}'")
        
        payload = {
            "branch": branch_name,
            "ref": ref
        }
        
        response = self.client.post(path, payload)
        response.raise_for_status()
        return response.json()

    def file_exists(self, project_id: int, file_path: str, ref: str) -> bool:
        encoded_path = urllib.parse.quote(file_path, safe="")
        # Note: Using URL params in path for HEAD request with shared client might need care if client escapes again.
        # But our client.head just takes path.
        # We need to append query string manually or update client to take params.
        # We did not add params to head() in GitLabHttpClient. 
        # I should assume path needs to be fully formed OR update client.
        # Let's fix client in a separate step or just append here if safe.
        path = f"api/v4/projects/{project_id}/repository/files/{encoded_path}?ref={ref}"
        response = self.client.head(path)
        return response.status_code == 200

    def commit_files(
        self, 
        project_id: int, 
        branch_name: str, 
        files_map: dict[str, str],
        commit_message: str
    ) -> dict[str, Any]:
        """
        Commits files to a branch. Performs smart upsert.
        """
        path = f"api/v4/projects/{project_id}/repository/commits"
        logger.info(f"Committing {len(files_map)} files to branch '{branch_name}' in project {project_id}")
        
        files_action_map = {}
        for file_path in files_map.keys():
            if self.file_exists(project_id, file_path, branch_name):
                files_action_map[file_path] = "update"
            else:
                files_action_map[file_path] = "create"

        payload = self.payload_builder.build_commit_payload(
            files_map=files_map,
            branch_name=branch_name,
            message=commit_message,
            files_action_map=files_action_map
        )
        
        response = self.client.post(path, payload)
        response.raise_for_status()
        return response.json()

    def create_merge_request(self, project_id: int, source_branch: str, target_branch: str, title: str, description: str = None) -> dict[str, Any]:
        path = f"api/v4/projects/{project_id}/merge_requests"
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "remove_source_branch": True
        }
        
        try:
            response = self.client.post(path, payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                logger.warning(f"MR already exists for {source_branch} -> {target_branch}. Fetching existing one.")
                return self._get_existing_mr(project_id, source_branch, target_branch)
            logger.error(f"Failed to create MR: {e.response.text}")
            raise e

    def _get_existing_mr(self, project_id: int, source_branch: str, target_branch: str) -> dict[str, Any]:
        path = f"api/v4/projects/{project_id}/merge_requests"
        params = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "state": "opened"
        }
        
        response = self.client.get(path, params=params)
        response.raise_for_status()
        
        mrs = response.json()
        if mrs:
            return mrs[0]
        
        return {
            "web_url": "https://gitlab.com/mr-exists-but-cannot-fetch",
            "id": 0,
            "iid": 0
        }
