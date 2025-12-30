import urllib.parse
from typing import Any

from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import GitLabHttpClient
from software_factory_poc.infrastructure.providers.vcs.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)

logger = LoggerFactoryService.build_logger(__name__)


class GitLabCommitService:
    def __init__(self, client: GitLabHttpClient, payload_builder: GitLabPayloadBuilderService):
        self.client = client
        self.payload_builder = payload_builder

    def file_exists(self, project_id: int, file_path: str, ref: str) -> bool:
        encoded_path = urllib.parse.quote(file_path, safe="")
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
