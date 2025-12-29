from dataclasses import dataclass
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

from software_factory_poc.application.core.services.scaffolding_contract_parser_service import ScaffoldingContractParserService
from software_factory_poc.infrastructure.providers.tools.jira.mappers.jira_adf_builder import JiraAdfBuilder

from software_factory_poc.configuration.tools.tool_settings import ToolSettings

@dataclass
class ProcessJiraRequestUseCase:
    agent: ScaffoldingAgent
    jira_provider: JiraProvider
    gitlab_provider: GitLabProvider
    settings: ToolSettings

    def execute(self, request: ScaffoldingRequest) -> str:
        issue_key = request.issue_key
        logger.info(f"Processing Jira Request for ticket {issue_key}")
        
        # Determine Lifecycle States from Config
        STATE_INITIAL = self.settings.workflow_state_initial
        STATE_SUCCESS = self.settings.workflow_state_success
        
        try:
            # Step 1: Notify Start
            self.jira_provider.add_comment(issue_key, "🤖 Iniciando tarea de scaffolding...")
            
            # Step 2: Parsing & Setup (Fail Fast)
            parser = ScaffoldingContractParserService()
            contract = parser.parse(request.raw_instruction)
            
            branch_name = f"feature/{issue_key}-scaffolding"
            project_path = contract.gitlab.project_path
            
            if not project_path:
                project_path = request.project_key

            project_id = self.gitlab_provider.resolve_project_id(project_path)
            
            # Step 3: Guard Check (Remote Idempotency)
            if self.gitlab_provider.branch_exists(project_id, branch_name):
                logger.info(f"Branch {branch_name} already exists. Skipping LLM generation.")
                info_msg = JiraAdfBuilder.build_info_panel(
                    title="ℹ️ Rama Existente Detectada",
                    details=f"La rama '{branch_name}' ya existe en el repositorio. Se asume que el trabajo fue generado previamente. La tarea pasará a revisión."
                )
                self.jira_provider.add_comment(issue_key, info_msg)
                self.jira_provider.transition_issue(issue_key, STATE_SUCCESS) 
                return "SKIPPED_BRANCH_EXISTS"
            
            # Step 4: Agent Execution (Core)
            generated_files = self.agent.execute_mission(request)
            
            # Security Check: Validate paths
            for file_path in generated_files.keys():
                if ".." in file_path or file_path.startswith("/") or "\\" in file_path:
                    raise ValueError(f"Security Error: Invalid file path generated '{file_path}'")
            
            # Step 5: Persistence (GitLab)
            self.gitlab_provider.create_branch(project_id, branch_name, "main")
            
            self.gitlab_provider.commit_files(
                project_id, 
                branch_name, 
                generated_files, 
                f"feat: Scaffolding for {issue_key}"
            )
            
            mr_response = self.gitlab_provider.create_merge_request(
                project_id,
                branch_name,
                "main",
                f"Scaffolding for {issue_key}: {request.summary}",
                description=f"Automated scaffolding for {issue_key}.\n\n{request.raw_instruction}"
            )
            mr_url = mr_response.get("web_url", "URL_NOT_FOUND")
            
            # Step 6: Notify Completion & Success Transition
            links = {"🔗 Ver Merge Request": mr_url}
            success_msg = JiraAdfBuilder.build_success_panel(
                title="✅ Tarea Completada",
                summary="El scaffolding ha sido generado correctamente.",
                links=links
            )
            self.jira_provider.add_comment(issue_key, success_msg)
            
            self.jira_provider.transition_issue(issue_key, STATE_SUCCESS)
            
            return mr_url

        except Exception as e:
            logger.error(f"Task failed for {issue_key}")
            logger.exception(e)
            
            # 1. Notify Failure
            try:
                # Sanitizar error para Jira (Evitar payload gigante)
                tech_detail = f"{type(e).__name__}: {str(e)}"
                error_summary = "La ejecución se detuvo debido a una excepción técnica. La tarea ha vuelto al estado inicial."

                error_msg = JiraAdfBuilder.build_error_panel(
                    error_summary=error_summary,
                    technical_detail=tech_detail
                )
                self.jira_provider.add_comment(issue_key, error_msg)
            except Exception as jira_err:
                logger.error(f"Failed to send error notification to Jira: {jira_err}")
            
            # 2. Attempt Rollback
            try:
                logger.info(f"Reverting issue {issue_key} to {STATE_INITIAL}")
                self.jira_provider.transition_issue(issue_key, STATE_INITIAL)
            except Exception as transition_err:
                logger.warning(f"Rollback status failed (ignoring): {transition_err}")
                
            raise e
