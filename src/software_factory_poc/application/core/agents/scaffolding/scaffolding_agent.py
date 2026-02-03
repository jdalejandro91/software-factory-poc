import logging
import re
from dataclasses import replace
from typing import List, Optional

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus
from software_factory_poc.application.core.agents.common.dtos.automation_context_dto import AutomationContextDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.scaffolding_contract import ScaffoldingContractModel
from software_factory_poc.application.core.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.agents.scaffolding.tools.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent

logger = logging.getLogger(__name__)


class ScaffoldingAgent(BaseAgent):
    """
    Orchestrator Agent for Scaffolding Tasks.
    Refactored for Clean Code, Composition, and Granular Responsibilities.
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

    def execute_flow(self, request: ScaffoldingOrder) -> None:
        """
        Main orchestration flow. Executes the scaffolding process sequentially.
        """
        try:
            self._report_start(request)

            # Phase 1: Preparation & Validation
            # Encapsulates contract parsing, security checks, ID resolution and branch validation.
            request, project_id, continue_flow = self._validate_preconditions(request)
            
            if not continue_flow:
                return

            # Phase 2: Intelligence (Research & Reasoning)
            research_context = self._execute_research_strategy(request)
            artifacts = self._generate_artifacts(request, research_context)

            # Phase 3: Execution (VCS Operations)
            branch_name = self._get_branch_name(request)
            self._create_feature_branch(project_id, branch_name)
            self._commit_artifacts(project_id, branch_name, artifacts, request)
            
            mr_link = self._create_merge_request(project_id, branch_name, request)

            # Phase 4: Finalization
            self._finalize_success(request, project_id, branch_name, mr_link)

        except Exception as e:
            self._handle_critical_failure(request, e)

    # --- Phase 1: Analysis & Validation Methods ---

    def _report_start(self, request: ScaffoldingOrder) -> None:
        self.reporter.report_start(request.issue_key, message="🚀 Iniciando generación de scaffolding...")

    def _validate_preconditions(self, request: ScaffoldingOrder) -> tuple[ScaffoldingOrder, int, bool]:
        """
        Performs all initial validations and setup:
        1. Parses the contract from the request.
        2. Overrides technical stack if specified in contract.
        3. Resolves Gitlab Project ID from repo path.
        4. Checks Security Permissions.
        5. Validates if the target branch already exists.

        Returns:
            - Updated ScaffoldingOrder (with tech stack override applied)
            - Resolved Project ID
            - Boolean flag: True if flow should continue, False if it should stop (e.g. branch exists).
        """
        # 1. Contract Parsing
        contract = self._parse_contract_or_fail(request)
        
        # 2. Tech Stack Override
        request = self._apply_tech_stack_override(request, contract)
        
        # 3. Target Repo Resolution & Project ID
        target_repo = self._resolve_target_repo(request, contract)
        project_id = self.vcs.resolve_project_id(target_repo)
        
        # 4. Security Check
        self._check_security_permissions(target_repo)

        # 5. Branch Existence Check
        branch_name = self._get_branch_name(request)
        existing_url = self.vcs.validate_branch(project_id, branch_name, target_repo)

        if existing_url:
            self._report_branch_exists(request, branch_name, existing_url)
            return request, project_id, False # Stop execution, task already done
            
        return request, project_id, True # Continue execution

    def _parse_contract_or_fail(self, request: ScaffoldingOrder) -> ScaffoldingContractModel:
        try:
            return ScaffoldingContractModel.from_raw_text(request.raw_instruction)
        except Exception as e:
            logger.error(f"Contract parsing failed: {e}")
            raise ValueError(f"Invalid Contract: {e}")

    def _apply_tech_stack_override(self, request: ScaffoldingOrder, contract: ScaffoldingContractModel) -> ScaffoldingOrder:
        if contract.technology_stack:
            logger.info(f"Override Tech Stack from Contract: {contract.technology_stack}")
            return replace(request, technology_stack=contract.technology_stack)
        return request

    def _resolve_target_repo(self, request: ScaffoldingOrder, contract: ScaffoldingContractModel) -> str:
        if contract.gitlab.project_path:
            return contract.gitlab.project_path
        if contract.gitlab.project_id:
            return str(contract.gitlab.project_id)
        if request.repository_url:
            return request.repository_url
        raise ValueError("Target repository not found in Contract or Request.")

    def _check_security_permissions(self, target_repo: str) -> None:
        if not self.config.project_allowlist:
            logger.warning("No allowlist configured. All groups allowed (INSECURE).")
            return

        group = target_repo.split("/")[0] if "/" in target_repo else target_repo
        if group not in self.config.project_allowlist:
            logger.warning(f"Security Block: Group '{group}' not in allowlist.")
            raise PermissionError(f"Security Policy Violation: Group '{group}' is not authorized.")

    def _report_branch_exists(self, request: ScaffoldingOrder, branch_name: str, url: str) -> None:
        msg = f"{ReporterMessages.BRANCH_EXISTS_PREFIX}{branch_name}|{url}"
        self.reporter.report_success(request.issue_key, msg)
        self.reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)

    # --- Phase 2: Intelligence Methods ---

    def _execute_research_strategy(self, request: ScaffoldingOrder) -> str:
        context_parts = []
        service_name = request.extra_params.get("service_name") if request.extra_params else None

        # 1. Project Context
        if service_name:
            context_parts.append(self._research_project_context(service_name))

        # 2. Global Standards
        if self.config.architecture_page_id:
            context_parts.append(self._research_global_standards())

        # 3. Fallback
        if not context_parts:
            context_parts.append(self._research_fallback(request.technology_stack))

        full_context = "\n\n".join(filter(None, context_parts))
        logger.info(f"Research completed. Total context length: {len(full_context)} chars.")
        return f"Research (Technical Context):\n{full_context}"

    def _research_project_context(self, service_name: str) -> Optional[str]:
        try:
            logger.info(f"🔎 Researching Project Context: '{service_name}'")
            ctx = self.researcher.research_project_technical_context(service_name)
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

    def _generate_artifacts(self, request: ScaffoldingOrder, context: str) -> List[FileContentDTO]:
        prompt = self.prompt_builder_tool.build_prompt(request, context)
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

    def _get_branch_name(self, request: ScaffoldingOrder) -> str:
        safe_key = re.sub(r'[^a-z0-9\-]', '', request.issue_key.lower())
        return f"feature/{safe_key}-scaffolding"

    def _create_feature_branch(self, project_id: int, branch_name: str) -> None:
        self.vcs.create_branch(project_id, branch_name, ref=self.config.default_target_branch)

    def _commit_artifacts(self, project_id: int, branch_name: str, artifacts: List[FileContentDTO], request: ScaffoldingOrder) -> None:
        files_map = self._prepare_files_map(artifacts)
        self.vcs.commit_files(
            project_id=project_id,
            branch_name=branch_name,
            files_map=files_map,
            message=f"Scaffolding for {request.issue_key}",
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

    def _create_merge_request(self, project_id: int, branch_name: str, request: ScaffoldingOrder) -> str:
        mr = self.vcs.create_merge_request(
            project_id=project_id,
            source_branch=branch_name,
            title=f"Scaffolding {request.issue_key}",
            description=f"Auto-generated.\n{request.summary}",
            target_branch=self.config.default_target_branch
        )
        logger.info(f"MR Created successfully. Link: {mr.web_url}")
        
        if not mr.web_url or not mr.web_url.startswith("http"):
            raise ValueError(f"Invalid MR Link generated: '{mr.web_url}'")
            
        return mr.web_url

    # --- Phase 4: Finalization Methods ---

    def _finalize_success(self, request: ScaffoldingOrder, project_id: int, branch_name: str, mr_link: str) -> None:
        # 1. Inject Automation Context
        context = AutomationContextDTO.from_values(
            project_id=str(project_id),
            branch=branch_name,
            mr_url=mr_link
        )
        self.reporter.save_automation_context(request.issue_key, context)

        # 2. Report Success Comment
        message_payload = {
            "type": "scaffolding_success",
            "title": "Scaffolding Completado Exitosamente",
            "summary": f"Se ha generado el código base para la tarea {request.issue_key}.\n{request.summary}",
            "links": {"🔗 Ver Merge Request": mr_link}
        }
        self.reporter.report_success(request.issue_key, message_payload)

        # 3. Transition
        self._transition_to_review(request)
        logger.info(f"Task {request.issue_key} completed successfully.")

    def _transition_to_review(self, request: ScaffoldingOrder) -> None:
        self.reporter.transition_task(request.issue_key, TaskStatus.IN_REVIEW)

    def _handle_critical_failure(self, request: ScaffoldingOrder, error: Exception) -> None:
        logger.error(f"Task {request.issue_key} failed: {error}", exc_info=True)
        self.reporter.report_failure(request.issue_key, str(error))
        
        # Optional: Transition back to TODO or keep in Progress depending on business rule
        self.reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
        logger.info(f"Error handled gracefully for task {request.issue_key}. Flow terminated.")