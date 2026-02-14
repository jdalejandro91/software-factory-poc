import re
from datetime import datetime
from typing import List, Optional, Any, Dict

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.ports.drivers.common.config.task_status import TaskStatus
from software_factory_poc.application.ports.drivers.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.ports.drivers.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.ports.drivers.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.ports.drivers.research import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.agents.scaffolding_prompt_builder import \
    ScaffoldingPromptBuilder
from software_factory_poc.application.ports.drivers.vcs.vcs_agent import VcsAgent
from software_factory_poc.domain.entities.task import Task
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ScaffoldingAgent(BaseAgent):
    """
    Orchestrator Agent for Scaffolding Tasks.
    Refactored to consume Domain Task Entity directly.
    """

    def __init__(
            self,
            config: ScaffoldingAgentConfig,
            reporter: ReporterAgent,
            vcs: VcsAgent,
            researcher: ResearchAgent,
            reasoner: ReasonerAgent
    ):
        super().__init__(name="ScaffoldingAgent", role="Orchestrator", goal="Orchestrate scaffolding creation")

        # Dependencies (Composition)
        self.config = config
        self.reporter = reporter
        self.vcs = vcs
        self.researcher = researcher
        self.reasoner = reasoner

        # Internal Tools
        self.prompt_builder_tool = ScaffoldingPromptBuilder()
        self.artifact_parser_tool = ArtifactParser()

    def execute_flow(self, task: Task) -> None:
        """
        Main orchestration flow. Executes the scaffolding process sequentially using Domain Task.
        """
        try:
            self._report_start(task)

            # Phase 1: Preparation & Validation
            # Config is already parsed in task.description.config
            task_config = task.description.config

            # extract key parameters
            tech_stack = task_config.get("technology_stack", "unknown")
            service_name = task_config.get("parameters", {}).get("service_name")

            target_repo, project_id, continue_flow = self._validate_preconditions(task, task_config)

            if not continue_flow:
                return

            # Phase 2: Intelligence (Research & Reasoning)
            research_context = self._execute_research_strategy(tech_stack, service_name)

            # Pass full config/task to prompt builder
            artifacts = self._generate_artifacts(task, research_context)

            # Phase 3: Execution (VCS Operations)
            branch_name = self._get_branch_name(task)
            self._create_feature_branch(project_id, branch_name)
            self._commit_artifacts(project_id, branch_name, artifacts, task)

            mr_link = self._create_merge_request(project_id, branch_name, task)

            # Phase 4: Finalization
            self._finalize_success(task, project_id, branch_name, mr_link)

        except Exception as e:
            self._handle_critical_failure(task, e)

    # --- Phase 1: Analysis & Validation Methods ---

    def _report_start(self, task: Task) -> None:
        self.reporter.report_start(task.key, message="🚀 Iniciando generación de scaffolding...")

    def _validate_preconditions(self, task: Task, config: Dict[str, Any]) -> tuple[str, int, bool]:
        """
        Validates target repo/Project ID, Security, and Branch existence.
        """
        # 1. Target Repo Resolution
        target_repo = self._resolve_target_repo(task, config)
        project_id = self.vcs.resolve_project_id(target_repo)

        # 2. Security Check
        self._check_security_permissions(target_repo)

        # 3. Branch Existence Check
        branch_name = self._get_branch_name(task)
        existing_url = self.vcs.validate_branch(project_id, branch_name)

        if existing_url:
            self._report_branch_exists(task, branch_name, existing_url, project_id)
            return target_repo, project_id, False  # Stop execution

        return target_repo, project_id, True  # Continue execution

    def _resolve_target_repo(self, task: Task, config: Dict[str, Any]) -> str:
        # Check config "target" -> "gitlab_project_path" or "gitlab_project_id"
        target = config.get("target", {})
        if target.get("gitlab_project_path"):
            return target.get("gitlab_project_path")
        if target.get("gitlab_project_id"):
            return str(target.get("gitlab_project_id"))

        if task.project_key:
            return f"generated/{task.project_key.lower()}"

        raise ValueError("Target repository not found in Task Configuration.")

    def _check_security_permissions(self, target_repo: str) -> None:
        if not self.config.project_allowlist:
            logger.warning("No allowlist configured. All groups allowed (INSECURE).")
            return

        group = target_repo.split("/")[0] if "/" in target_repo else target_repo
        if group not in self.config.project_allowlist:
            logger.warning(f"Security Block: Group '{group}' not in allowlist.")
            raise PermissionError(f"Security Policy Violation: Group '{group}' is not authorized.")

    def _report_branch_exists(self, task: Task, branch_name: str, url: str, project_id: int) -> None:
        logger.warning(
            f"🛑 STOPPING FLOW: Branch '{branch_name}' already exists. URL: {url}. To regenerate, delete this branch in GitLab.")

        # Check for active MR
        mr_url = self.vcs.gateway.get_active_mr_url(project_id, branch_name)

        links = {}
        if mr_url:
            links["🔗 Ver Merge Request Existing"] = mr_url
        else:
            links["🔗 Ver Rama Existente"] = url

        message_payload = {
            "type": "scaffolding_exists",
            "title": "⚠️ El Scaffolding ya existe",
            "summary": "Se detectó que la rama ya existe en el repositorio. No se realizaron cambios nuevos.",
            "links": links
        }

        self.reporter.report_success(task.key, message_payload)
        self.reporter.transition_task(task.key, TaskStatus.IN_REVIEW)

    # --- Phase 2: Intelligence Methods ---

    def _execute_research_strategy(self, tech_stack: str, service_name: Optional[str]) -> str:
        context_parts = []

        # 1. Project Context
        if service_name:
            context_parts.append(self._research_project_context(service_name))

        # 2. Global Standards
        if self.config.architecture_page_id:
            context_parts.append(self._research_global_standards())

        # 3. Fallback
        if not context_parts:
            context_parts.append(self._research_fallback(tech_stack))

        full_context = "\n\n".join(filter(None, context_parts))
        logger.info(f"Research completed. Total context length: {len(full_context)} chars.")
        return f"Research (Technical Context):\n{full_context}"

    def _research_project_context(self, service_name: str) -> Optional[str]:
        try:
            logger.info(f"🔎 Researching Project Context: '{service_name}'")
            ctx = self.researcher.research_project_technical_context(service_name)

            if ctx:
                logger.info(f"📚 Project Context Loaded. Length: {len(ctx)} chars.")
                logger.debug(f"Context Preview:\n{ctx[:500]}...")
            else:
                logger.warning(f"⚠️ No technical context found for service '{service_name}'")

            if "ADVERTENCIA" in ctx or "ERROR" in ctx:
                return f"=== REQUISITOS DEL PROYECTO (ADVERTENCIA) ===\n{ctx}"
            return f"=== REQUISITOS DEL PROYECTO ===\n{ctx}"
        except Exception as e:
            logger.warning(f"Project context research failed: {e}")
            return None

    def _research_global_standards(self) -> Optional[str]:
        try:
            logger.info(f"🔎 Researching Global Standards (Page ID: {self.config.architecture_page_id})")
            ctx = self.researcher.investigate("", specific_page_id=self.config.architecture_page_id)
            return f"=== ESTÁNDARES DE ARQUITECTURA ===\n{ctx}" if ctx else None
        except Exception as e:
            logger.warning(f"Global standards research failed: {e}")
            return None

    def _research_fallback(self, stack: str) -> str:
        query = f"Architecture standards for {stack} enterprise projects"
        logger.info(f"🔎 executing Fallback Research: {query}")
        return f"=== CONTEXTO GENERAL ===\n{self.researcher.investigate(query)}"

    def _generate_artifacts(self, task: Task, context: str) -> List[FileContentDTO]:
        prompt = self.prompt_builder_tool.build_prompt_from_task(task, context)
        model_id = self._resolve_model_id()

        raw_response = self.reasoner.reason(prompt, model_id)
        artifacts = self.artifact_parser_tool.parse_response(raw_response)

        if not artifacts:
            raise ValueError("LLM generated 0 artifacts. Cannot proceed.")

        return artifacts

    def _resolve_model_id(self) -> str | List[str]:
        if self.config.llm_model_priority:
            return [m.qualified_name for m in self.config.llm_model_priority]

        if self.config.model_name:
            return self.config.model_name

        logger.warning("No model configured. Fallback to default.")
        return "openai:gpt-4-turbo"

    # --- Phase 3: Execution Methods ---

    def _get_branch_name(self, task: Task) -> str:
        safe_key = re.sub(r'[^a-z0-9\-]', '', task.key.lower())
        return f"feature/{safe_key}-scaffolding"

    def _create_feature_branch(self, project_id: int, branch_name: str) -> None:
        self.vcs.create_branch(project_id, branch_name, ref=self.config.default_target_branch)

    def _commit_artifacts(self, project_id: int, branch_name: str, artifacts: List[FileContentDTO], task: Task) -> None:
        files_map = self._prepare_files_map(artifacts)
        self.vcs.commit_files(
            project_id=project_id,
            branch_name=branch_name,
            files_map=files_map,
            message=f"Scaffolding for {task.key}",
            force_create=False
        )

    def _prepare_files_map(self, artifacts: List[FileContentDTO]) -> dict[str, str]:
        files_map = {}
        for artifact in artifacts:
            clean_path = artifact.path.lstrip("/")
            if clean_path in files_map:
                logger.warning(f"Duplicate path generated: {clean_path}. Overwriting.")
            files_map[clean_path] = artifact.content
        return files_map

    def _create_merge_request(self, project_id: int, branch_name: str, task: Task) -> str:
        mr = self.vcs.create_merge_request(
            project_id=project_id,
            source_branch=branch_name,
            title=f"Scaffolding {task.key}",
            description=f"Auto-generated.\n{task.summary}",
            target_branch=self.config.default_target_branch
        )
        logger.info(f"MR Created successfully. Link: {mr.web_url}")

        if not mr.web_url or not mr.web_url.startswith("http"):
            raise ValueError(f"Invalid MR Link generated: '{mr.web_url}'")

        return mr.web_url

    # --- Phase 4: Finalization Methods ---

    def _finalize_success(self, task: Task, project_id: int, branch_name: str, mr_link: str) -> None:
        """
        Finalizes the task by updating metadata and transitioning status.
        """
        # 1. Prepare Explicit Context Dictionary (Nested)
        # This ensures parameters appear under 'code_review_params' key in the final YAML
        context = {
            "code_review_params": {
                "gitlab_project_id": str(project_id),
                "source_branch_name": branch_name,
                "review_request_url": mr_link,
                "generated_at": datetime.utcnow().isoformat()
            }
        }

        # 2. Update Task Entity (Deep Merge)
        updated_task = task.update_metadata(context)
        logger.info(f"Metadata updated. Config keys: {list(updated_task.description.config.keys())}")
        
        # 3. Update Jira Description
        self.reporter.update_task_description(task.key, updated_task.description)

        # 4. Report Success Comment
        message_payload = {
            "type": "scaffolding_success",
            "title": "Scaffolding Completado Exitosamente",
            "summary": f"Se ha generado el código base para la tarea {task.key}.\n{task.summary}",
            "links": {"🔗 Ver Merge Request": mr_link}
        }
        self.reporter.report_success(task.key, message_payload)

        # 5. Transition
        self._transition_to_review(task)
        logger.info(f"Task {task.key} completed successfully.")

    def _transition_to_review(self, task: Task) -> None:
        self.reporter.transition_task(task.key, TaskStatus.IN_REVIEW)

    def _handle_critical_failure(self, task: Task, error: Exception) -> None:
        logger.error(f"Task {task.key} failed: {error}", exc_info=True)
        self.reporter.report_failure(task.key, str(error))

        self.reporter.transition_task(task.key, TaskStatus.TO_DO)
        logger.info(f"Error handled gracefully for task {task.key}. Flow terminated.")