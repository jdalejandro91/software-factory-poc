from dataclasses import dataclass
from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort, TaskStatus
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError

@dataclass
class ReporterAgent(BaseAgent):
    """
    Agent responsible for reporting progress and status to the Task Tracker (Jira).
    """
    gateway: TaskTrackerGatewayPort

    def announce_start(self, task_id: str) -> None:
        self.gateway.add_comment(task_id, "🤖 Iniciando tarea de scaffolding...")

    def announce_completion(self, task_id: str, resource_url: str) -> None:
         self.gateway.add_comment(task_id, f"✅ Scaffolding exitoso. MR: {resource_url}")
         self.gateway.transition_status(task_id, TaskStatus.IN_REVIEW)

    def announce_failure(self, task_id: str, error: Exception) -> None:
        is_domain_error = isinstance(error, DomainError)
        error_type = "Error de Dominio" if is_domain_error else "Error Técnico"
        msg = f"❌ Fallo en generación ({error_type}): {str(error)}"
        
        self.gateway.add_comment(task_id, msg)
        self.gateway.transition_status(task_id, TaskStatus.TO_DO)

    def announce_redundancy(self, task_id: str, resource_url: str) -> None:
        # Format: ℹ️ BRANCH_EXISTS|generic|{url}
        self.gateway.add_comment(task_id, f"ℹ️ BRANCH_EXISTS|generic|{resource_url}")
        self.gateway.transition_status(task_id, TaskStatus.IN_REVIEW)
