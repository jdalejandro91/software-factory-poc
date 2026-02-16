import urllib.parse
from typing import Any, Optional

from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.drivers.vcs.clients.gitlab_http_client import GitLabHttpClient

logger = LoggerFactoryService.build_logger(__name__)


class GitLabBranchService:
    def __init__(self, client: GitLabHttpClient):
        self.client = client

    def get_branch(self, project_id: int, branch_name: str) ->Optional[ dict[str, Any]]:
        """
        Checks if a branch exists. Returns branch info or None.
        """
        encoded_branch = urllib.parse.quote(branch_name, safe="")
        path = f"api/v4/projects/{project_id}/repository/branches/{encoded_branch}"
        
        response = self.client.get(path)
        if response.status_code == 200:
            return response.json()
        return None

    def branch_exists(self, project_id: int, branch_name: str) -> bool:
        """
        Checks if a branch exists in the project.
        """
        safe_branch = urllib.parse.quote(branch_name, safe="")
        
        try:
            logger.info(f"Checking if branch '{branch_name}' exists in project {project_id}...")
            response = self.client.get(f"api/v4/projects/{project_id}/repository/branches/{safe_branch}")
            
            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            return False
        except Exception as e:
            # Re-raise only if not a 404-like error handled by client (if client raises on 404)
            # But here we handled 404 explicitly above.
            # If client raises exception on connection error, we let it bubble.
            logger.error(f"Error checking branch existence: {e}")
            raise e

    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> dict[str, Any]:
        """Creates a branch. Returns existing one if conflict occurs."""
        path = f"api/v4/projects/{project_id}/repository/branches"
        logger.info(f"Creating branch '{branch_name}' from '{ref}'")
        
        try:
            response = self.client.post(path, {"branch": branch_name, "ref": ref})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code in [400, 409]:
                logger.info(f"Branch '{branch_name}' already exists.")
                return self.get_branch(project_id, branch_name) or {}
            raise e
