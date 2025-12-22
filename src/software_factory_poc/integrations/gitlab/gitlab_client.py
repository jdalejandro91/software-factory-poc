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
        
        # Usamos PRIVATE-TOKEN por defecto
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

    def get_branch(self, project_id: int, branch_name: str) -> Dict[str, Any] | None:
        """
        Checks if a branch exists. Returns branch info or None.
        """
        encoded_branch = urllib.parse.quote(branch_name, safe="")
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/branches/{encoded_branch}"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers(), timeout=10.0)
            if response.status_code == 200:
                return response.json()
            return None

    def create_branch(self, project_id: int, branch_name: str, ref: str) -> Dict[str, Any]:
        """
        Creates a new branch from a reference (e.g. main).
        Idempotent: If branch exists, returns existing info.
        """
        # 1. Check existence
        existing_branch = self.get_branch(project_id, branch_name)
        if existing_branch:
            logger.info(f"Branch '{branch_name}' already exists in project {project_id}. Skipping creation.")
            return existing_branch

        # 2. Create
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

    def file_exists(self, project_id: int, file_path: str, ref: str) -> bool:
        """
        Checks if a file exists in the repository at a given ref using HEAD.
        """
        encoded_path = urllib.parse.quote(file_path, safe="")
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}?ref={ref}"
        
        with httpx.Client() as client:
            response = client.head(url, headers=self._get_headers(), timeout=5.0)
            return response.status_code == 200

    def commit_files(
        self, 
        project_id: int, 
        branch_name: str, 
        files_map: Dict[str, str], 
        commit_message: str
    ) -> Dict[str, Any]:
        """
        Commits files to a branch.
        Smart Upsert: Checks if file exists to determine 'create' or 'update' action.
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
        logger.info(f"Committing {len(files_map)} files to branch '{branch_name}' in project {project_id}")
        
        # Calculate actions
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
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=20.0)
            response.raise_for_status()
            return response.json()

    def create_merge_request(self, project_id: int, source_branch: str, target_branch: str, title: str, description: str = None) -> str:
        """
        Crea un MR. Si ya existe (409 Conflict), busca el existente y devuelve su URL (Idempotencia).
        """
        # CORRECCIÓN: Agregado /api/v4
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests"
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "remove_source_branch": True
        }
        
        try:
            response = httpx.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return response.json()["web_url"]

        except httpx.HTTPStatusError as e:
            # Manejo de conflicto (Ya existe el MR)
            if e.response.status_code == 409:
                logger.warning(f"MR already exists for {source_branch} -> {target_branch}. Fetching existing one.")
                return self._get_existing_mr_url(project_id, source_branch, target_branch)
            
            # Si es otro error, lanzarlo
            logger.error(f"Failed to create MR: {e.response.text}")
            raise e

    def _get_existing_mr_url(self, project_id: int, source_branch: str, target_branch: str) -> str:
        """
        Helper para buscar un MR existente cuando falla la creación por duplicado.
        """
        # CORRECCIÓN: Agregado /api/v4
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests"
        params = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "state": "opened" # Solo nos interesan los abiertos
        }
        
        response = httpx.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        
        mrs = response.json()
        if mrs:
            return mrs[0]["web_url"]
        
        # Caso raro: Dio 409 pero no lo encontramos (tal vez está cerrado/merged)
        return "https://gitlab.com/mr-exists-but-cannot-fetch"
