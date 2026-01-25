from dataclasses import dataclass
from software_factory_poc.application.core.domain.agents.base_agent import BaseAgent
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort, TaskStatus


@dataclass
class ReporterAgent(BaseAgent):
    """
    Agent responsible for reporting progress and status to the Task Tracker (Jira).
    """
    gateway: TaskTrackerGatewayPort

    def report_start(self, task_id: str) -> None:
        self.gateway.add_comment(task_id, "🤖 Iniciando tarea de scaffolding...")

    def report_success(self, task_id: str, message: str) -> None:
        self.gateway.add_comment(task_id, f"✅ Éxito: {message}")

    def report_failure(self, task_id: str, error_msg: str) -> None:
        self.gateway.add_comment(task_id, f"❌ Fallo: {error_msg}")

    def transition_task(self, task_id: str, status: TaskStatus) -> None:
        self.gateway.transition_status(task_id, status)
