import urllib.parse
from typing import Any

from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.adapters.drivers.vcs.clients.gitlab_http_client import GitLabHttpClient
from software_factory_poc.infrastructure.adapters.drivers.vcs.mappers.gitlab_payload_builder_service import (
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
        commit_message: str,
        force_create: bool = False
    ) -> dict[str, Any]:
        """
        Commits files to a branch. Performs smart upsert or forced creation.
        """
        if not files_map:
            logger.warning("Commit requested with empty files_map. Skipping.")
            return {}

        logger.info(f"Committing {len(files_map)} files to branch '{branch_name}' (Project: {project_id})")
        
        files_action_map = self._prepare_actions(project_id, branch_name, files_map, force_create)
        return self._send_commit(project_id, branch_name, files_map, commit_message, files_action_map)

    def _prepare_actions(self, project_id: int, branch_name: str, files_map: dict[str, str], force_create: bool) -> dict[str, str]:
        actions = {}
        for file_path in files_map.keys():
            if force_create:
                actions[file_path] = "create"
            elif self.file_exists(project_id, file_path, branch_name):
                actions[file_path] = "update"
            else:
                actions[file_path] = "create"
        return actions

    def _send_commit(self, project_id: int, branch_name: str, files_map: dict, message: str, actions_map: dict) -> dict:
        payload = self.payload_builder.build_commit_payload(
            files_map=files_map,
            branch_name=branch_name,
            message=message,
            files_action_map=actions_map
        )
        path = f"api/v4/projects/{project_id}/repository/commits"
        response = self.client.post(path, payload)
        response.raise_for_status()
        return response.json()
