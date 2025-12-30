from typing import Any
import urllib.parse
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import GitLabHttpClient

logger = LoggerFactoryService.build_logger(__name__)


class GitLabBranchService:
    def __init__(self, client: GitLabHttpClient):
        self.client = client

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
            if "404" in str(e): 
                return False
            logger.error(f"Error checking branch existence: {e}")
            raise e

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
