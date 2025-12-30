from dataclasses import dataclass

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.core.domain.entities.task.task import Task
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError
from software_factory_poc.application.core.domain.services.prompt_builder_service import PromptBuilderService

@dataclass
class ScaffoldingAgent:
    """
    Domain Service / Aggregate responsible for Scaffolding business logic.
    Encapsulates how a Task reacts to events.
    """

    def build_prompt(self, request: ScaffoldingRequest, context: str) -> str:
        """
        Builds the full prompt for the LLM.
        """
        full_system_prompt = PromptBuilderService.build_system_prompt(request.technology_stack)
        # We assume PromptBuilderService.build_user_prompt handles concatenation of instruction + context
        full_user_prompt = PromptBuilderService.build_user_prompt(request.raw_instruction, context)
        return f"{full_system_prompt}\n\n{full_user_prompt}"

    def validate_files(self, files: list[object]) -> None:
        """
        Validates the generated files.
        Raises DomainError if invalid.
        """
        if not files:
            raise DomainError("Generated files list is empty.")
        # Additional validation logic can go here (e.g. check for index file etc.)

    def report_success(self, task: Task, mr_link: str, gateway: TaskTrackerGatewayPort) -> None:
        """
        Reports success to the tracker.
        """
        msg = f"✅ Scaffolding exitoso. MR: {mr_link}"
        gateway.add_comment(task.id, msg)
        gateway.transition_status(task.id, TaskStatus.IN_REVIEW)

    def report_failure(self, task: Task, error: Exception, gateway: TaskTrackerGatewayPort) -> None:
        """
        Reports failure to the tracker.
        """
        error_type = "Error de Dominio" if isinstance(error, DomainError) else "Error Técnico"
        msg = f"❌ Fallo en generación ({error_type}): {str(error)}"
        
        gateway.add_comment(task.id, msg)
        gateway.transition_status(task.id, TaskStatus.TO_DO)

    def report_existing_branch(self, task: Task, branch: str, gateway: TaskTrackerGatewayPort) -> None:
        """
        Reports that a branch already exists.
        """
        msg = f"ℹ️ La rama {branch} ya existe. Se omite generación."
        gateway.add_comment(task.id, msg)
        gateway.transition_status(task.id, TaskStatus.IN_REVIEW)
