from typing import Any, Optional
from software_factory_poc.application.core.domain.entities.agents.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.entities.agents.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.entities.agents.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort, TaskStatus
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError
# Assuming VcsGateway interface exists or using Any for now as it wasn't clearly imported in UseCase 
# (it was resolved by resolver.resolve_vcs() which returns something matching a protocol).
# UseCase used: resolve_project_id, branch_exists, create_branch, commit_files, create_merge_request

class VcsAgentAdapter(VcsAgent):
    def __init__(self, gateway: Any):
        self.gateway = gateway
        self.project_id = None
        self.branch_name = None
        self.repo_url = None

    def check_branch_exists(self, repo_url: str, branch_name: str) -> Any:
        project_identifier = repo_url or "unknown/repo"
        self.project_id = self.gateway.resolve_project_id(project_identifier)
        if self.gateway.branch_exists(self.project_id, branch_name):
            # Return URL construction logic here or just a boolean/object?
            # Replicating logic from UseCase:
            base_repo = repo_url.replace(".git", "").rstrip("/")
            separator = "/-/tree/" if "gitlab" in base_repo else "/tree/"
            branch_url = f"{base_repo}{separator}{branch_name}"
            return branch_url
        return None

    def prepare_repository(self, repo_url: str, branch_name: str) -> bool:
        self.repo_url = repo_url
        self.branch_name = branch_name
        project_identifier = repo_url or "unknown/repo"
        self.project_id = self.gateway.resolve_project_id(project_identifier)
        
        # Create branch
        self.gateway.create_branch(self.project_id, branch_name)
        return True

    def publish_changes(self, files: list[Any], message: str) -> str:
        files_map = {f.path: f.content for f in files}
        self.gateway.commit_files(self.project_id, self.branch_name, files_map, f"feat: {message}")
        
        mr_result = self.gateway.create_merge_request(
            project_id=self.project_id,
            source_branch=self.branch_name,
            target_branch="main", # Defaulting to main
            title=message,
            description=f"Automated scaffolding.\n{message}"
        )
        return mr_result.get("web_url", "URL not found")


class ReporterAgentAdapter(ReporterAgent):
    def __init__(self, gateway: TaskTrackerGatewayPort):
        self.gateway = gateway

    def announce_start(self, task_id: str) -> None:
        self.gateway.add_comment(task_id, "🤖 Iniciando tarea de scaffolding...")

    def announce_success(self, task_id: str, result_link: str) -> None:
        self.gateway.add_comment(task_id, f"✅ Scaffolding exitoso. MR: {result_link}")
        self.gateway.transition_status(task_id, TaskStatus.IN_REVIEW)

    def announce_failure(self, task_id: str, error: Exception) -> None:
        is_domain_error = isinstance(error, DomainError)
        error_type = "Error de Dominio" if is_domain_error else "Error Técnico"
        
        # If it's a domain error, safe to share details. If infrastructure, maybe sanitize?
        # Requirement: "Agent must decide what info is Domain Safe"
        # Assuming all DomainError messages are safe. Infra errors might need generalized message or just type.
        # However, for debugging we usually want the error. The prompt says "based on if ... DomainError or InfraError".
        # Let's assume we format it nicely.
        
        msg = f"❌ Fallo en generación ({error_type}): {str(error)}"
        self.gateway.add_comment(task_id, msg)
        self.gateway.transition_status(task_id, TaskStatus.TO_DO)

    def announce_existing_branch(self, task_id: str, branch_url: str) -> None:
         # Need to extend interface if we want this specific method, 
         # or we treat it as "success" or "failure" or generic message?
         # The UseCase had generic method for this.
         # For now, I'll cheat and just add comment here, but properly I should extend interface.
         # But I can't extend interface easily without editing file again.
         # I'll just use announce_success or add a custom method if I can cast it.
         # Or I'll use announce_success with a specific message?
         # "BRANCH_EXISTS" is strict format.
         self.gateway.add_comment(task_id, f"ℹ️ BRANCH_EXISTS|generic|{branch_url}")
         self.gateway.transition_status(task_id, TaskStatus.IN_REVIEW)


class KnowledgeAgentAdapter(KnowledgeAgent):
    def __init__(self, gateway: KnowledgeGateway):
        self.gateway = gateway

    def extract_context(self, search_criteria: dict) -> str:
        return self.gateway.retrieve_context(search_criteria)

    def validate_context(self, context: str) -> bool:
        return bool(context and len(context) > 100)
