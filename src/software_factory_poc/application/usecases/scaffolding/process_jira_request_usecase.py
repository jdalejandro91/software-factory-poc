from dataclasses import dataclass
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

from software_factory_poc.application.core.services.scaffolding_contract_parser_service import ScaffoldingContractParserService
from software_factory_poc.infrastructure.providers.tools.jira.mappers.jira_adf_builder import JiraAdfBuilder

@dataclass
class ProcessJiraRequestUseCase:
    agent: ScaffoldingAgent
    jira_provider: JiraProvider
    gitlab_provider: GitLabProvider

    def execute(self, request: ScaffoldingRequest) -> str:
        issue_key = request.issue_key
        logger.info(f"Processing Jira Request for ticket {issue_key}")
        
        try:
            # Step 1: Notify Start
            self.jira_provider.add_comment(issue_key, "🤖 Iniciando agente de scaffolding...")
            # Optional: Transition to 'In Progress' - skipping ID lookup complexity for now or assuming explicit ID if known
            
            # Step 2: Agent Execution (Core)
            # This invokes the retry logic + architectural knowledge retrieval
            generated_files = self.agent.execute_mission(request)
            
            # Security Check: Validate paths
            for file_path in generated_files.keys():
                if ".." in file_path or file_path.startswith("/") or "\\" in file_path:
                    raise ValueError(f"Security Error: Invalid file path generated '{file_path}'")
            
            # Step 3: Persistence (GitLab)
            branch_name = f"feature/{issue_key}-scaffolding"
            
            # Resolve Project Path from Contract
            parser = ScaffoldingContractParserService()
            contract = parser.parse(request.raw_instruction)
            project_path = contract.gitlab.project_path
            
            if not project_path:
                # Fallback to Jira project key if not in contract (or raise error if mandatory)
                # But contract validation should handle it.
                # If parsed model returns None, we use request.project_key ?
                # User says: "use that value". 
                project_path = request.project_key

            # Resolve ID if needed, strict DDD usually implies ID in request or separate resolution service
            # For now relying on provider to handle resolution or passed ID
            # Re-reading GitLabProvider: resolve_project_id(project_path)
            project_id = self.gitlab_provider.resolve_project_id(project_path)
            
            # Ensure branch exists/created
            self.gitlab_provider.create_branch(project_id, branch_name, "main")
            
            # Commit files (Agent returns Dict[str, str] mapping filenames to content)
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
            
            # Step 4: Notify Completion
            links = {"Ver Merge Request": mr_url}
            success_msg = JiraAdfBuilder.build_success_panel(
                title="🚀 Misión Cumplida: Scaffolding Generado",
                summary=f"El agente ha generado exitosamente el código base para: {request.summary}",
                links=links
            )
            self.jira_provider.add_comment(issue_key, success_msg)
            
            self.jira_provider.transition_issue(issue_key, "Done")
            
            return mr_url

        except Exception as e:
            logger.error(f"Mission failed for {issue_key}")
            logger.exception(e)
            
            # 1. Notify Failure
            try:
                error_detail = str(e)
                steps = [
                    "Se detuvo la generación de código.",
                    "Se ha revertido el estado de la tarea a 'To Do'.",
                    "Por favor revise los inputs del contrato YAML."
                ]
                error_msg = JiraAdfBuilder.build_error_panel(
                    title="⚠️ Misión Abortada",
                    error_detail=error_detail,
                    steps_taken=steps
                )
                self.jira_provider.add_comment(issue_key, error_msg)
            except Exception as jira_err:
                logger.error(f"Failed to send error notification to Jira: {jira_err}")
            
            # 2. Attempt Rollback
            try:
                self.jira_provider.transition_issue(issue_key, "To Do")
            except Exception as transition_err:
                logger.warning(f"Failed to rollback Jira status: {transition_err}")
                
            raise e
