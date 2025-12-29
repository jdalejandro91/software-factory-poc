from dataclasses import dataclass
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

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
            scaffolding_content = self.agent.execute_mission(request)
            
            # Step 3: Persistence (GitLab)
            branch_name = f"feature/{issue_key}-scaffolding"
            project_path = request.project_key # Assuming project_key maps to path or ID logic needed
            
            # Resolve ID if needed, strict DDD usually implies ID in request or separate resolution service
            # For now relying on provider to handle resolution or passed ID
            # Re-reading GitLabProvider: resolve_project_id(project_path)
            project_id = self.gitlab_provider.resolve_project_id(project_path)
            
            # Ensure branch exists/created
            self.gitlab_provider.create_branch(project_id, branch_name, "main")
            
            # Commit files (Using a simple map for now, assuming content is a single file or need parsing)
            # The agent return 'str', but commit_files expects map.
            # Assuming agent returns raw code or packaged structure. 
            # Prompt 2 context implies "scaffolding_content" is what we commit.
            # I will wrap it in a default file if strict map needed, e.g. "scaffold.py" or parse headers?
            # User instruction: "content: scaffolding_content". 
            # Commit needs map: { "filename": content }
            # I'll check ScaffoldingAgent output format. 
            # Agent returns `str`.
            # I will assume "generated_scaffold.py" or use a parser if available.
            # For this step, I'll use a placeholder filename "generated_code.py" or similar.
            files_map = {"generated_scaffolding.py": scaffolding_content}
            self.gitlab_provider.commit_files(
                project_id, 
                branch_name, 
                files_map, 
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
            
            # Step 4: Notify Success
            self.jira_provider.add_comment(issue_key, f"✅ Misión completada. MR creado: {mr_url}")
            
            return scaffolding_content

        except Exception as e:
            # Step 5: Error Handling
            logger.exception(f"Mission failed for {issue_key}")
            error_msg = f"❌ Error en la misión: {str(e)}"
            self.jira_provider.add_comment(issue_key, error_msg)
            raise e
