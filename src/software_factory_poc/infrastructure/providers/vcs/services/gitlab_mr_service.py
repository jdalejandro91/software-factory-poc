from typing import Any
import httpx
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import GitLabHttpClient

logger = LoggerFactoryService.build_logger(__name__)


class GitLabMrService:
    def __init__(self, client: GitLabHttpClient):
        self.client = client

    def create_merge_request(self, project_id: int, source_branch: str, target_branch: str, title: str, description: str | None = None) -> dict[str, Any]:
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
        
        # If we got 409 but can't find it, raise error
        logger.error(f"GitLab reporting conflict but could not find open MR for {source_branch} -> {target_branch}")
        raise ValueError(f"MR conflict detected but could not be resolved.")
