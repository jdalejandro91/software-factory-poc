from dataclasses import dataclass

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.core.domain.entities.task.task import Task
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError
from software_factory_poc.application.core.domain.services.prompt_builder_service import PromptBuilderService
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway

@dataclass
class ScaffoldingAgent:
    """
    Domain Service / Aggregate responsible for Scaffolding business logic.
    Encapsulates how a Task reacts to events.
    """

    def search_knowledge(self, gateway: "KnowledgeGateway", search_filters: dict) -> str:
        """
        Orchestrates knowledge retrieval via the gateway using specific filters.
        """
        # 1. Ejecutar búsqueda
        context = gateway.retrieve_context(search_filters)

        # 2. Validaciones de Dominio (Calidad del contexto)
        if not context or len(context.strip()) == 0:
            # No lanzamos error, pero retornamos un indicador claro para el prompt
            return "No knowledge found."

        if len(context) < 100:
            logging.getLogger(__name__).warning("Suspiciously small knowledge context retrieved (<100 chars).")

        return context

    def build_prompt(self, request: ScaffoldingRequest, context: str) -> str:
        """
        Delegates to PromptBuilderService to construct the full LLM prompt.
        """
        return PromptBuilderService.build_scaffolding_prompt(request, context)

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
