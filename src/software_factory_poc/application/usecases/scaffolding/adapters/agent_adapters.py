import logging
from typing import Any, List, Optional, Dict

from software_factory_poc.application.core.domain.agents.capabilities.reasoning_agent import ReasoningAgent
from software_factory_poc.application.core.domain.agents.capabilities.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.capabilities.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.domain.agents.capabilities.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.capabilities.reporter_agent import ReporterAgent

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.ports.gateways.dtos import FileContent
from software_factory_poc.application.core.ports.gateways.llm_gateway import LlmGateway
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort, TaskStatus
from software_factory_poc.application.core.ports.gateways.vcs_gateway import VcsGateway

from software_factory_poc.application.core.domain.services.prompt_builder_service import PromptBuilderService
from software_factory_poc.application.core.domain.services.file_parsing_service import FileParsingService
from software_factory_poc.application.core.domain.exceptions.domain_error import DomainError

logger = logging.getLogger(__name__)

class ReasoningAgentAdapter(ReasoningAgent):
    def __init__(self, llm_gateway: LlmGateway, model_name: str = "gpt-4-turbo"):
        self.llm_gateway = llm_gateway
        self.model_name = model_name

    def generate_scaffolding(self, request: ScaffoldingRequest, context: str) -> List[FileContent]:
        # 1. Build Prompt
        prompt = PromptBuilderService.build_scaffolding_prompt(request, context)
        
        # 2. Call LLM
        llm_response = self.llm_gateway.generate_code(prompt=prompt, model=self.model_name)
        
        # 3. Parse Response
        files = FileParsingService.parse_llm_response(llm_response)
        
        # 4. Validate
        if not files:
            raise ValueError("Generated files list is empty. LLM failed to produce valid code blocks.")
            
        return files

class ResearchAgentAdapter(ResearchAgent):
    def __init__(self, gateway: KnowledgeGateway):
        self.gateway = gateway

    def investigate(self, query: str, filters: Dict) -> str:
        # Merge query into filters/criteria if needed, or pass as part of dict
        # Typically gateway.retrieve_context takes a dict.
        search_criteria = {**filters, "query": query}
        context = self.gateway.retrieve_context(search_criteria)
        
        if not context or len(context) < 100:
             logger.warning(f"Context retrieval yielded empty or short result for query: {query}")
             
        return context

class KnowledgeAgentAdapter(KnowledgeAgent):
    def __init__(self, gateway: KnowledgeGateway):
        self.gateway = gateway

    def retrieve_similar_solutions(self, topic: str) -> str:
        logger.info("Knowledge retrieval skipped (not configured yet).")
        return ""

class VcsAgentAdapter(VcsAgent):
    def __init__(self, gateway: VcsGateway):
        self.gateway = gateway
        self.project_id = None
        self.branch_name = None

    def branch_exists(self, repo_url: str, branch_name: str) -> Optional[str]:
        project_identifier = repo_url or "unknown/repo"
        # Cache project_id for later use in this session
        self.project_id = self.gateway.resolve_project_id(project_identifier)
        
        if self.gateway.branch_exists(self.project_id, branch_name):
            # Construct URL manually for robustness
            base_repo = repo_url.replace(".git", "").rstrip("/")
            # Initial simple heuristic for GitLab vs others
            separator = "/-/tree/" if "gitlab" in base_repo else "/tree/"
            return f"{base_repo}{separator}{branch_name}"
            
        return None

    def prepare_workspace(self, repo_url: str, branch_name: str) -> None:
        self.branch_name = branch_name
        project_identifier = repo_url or "unknown/repo"
        if not self.project_id:
             self.project_id = self.gateway.resolve_project_id(project_identifier)
        
        self.gateway.create_branch(self.project_id, branch_name)

    def publish_changes(self, files: List[FileContent], message: str) -> str:
        # 1. Transform to dict {path: content}
        files_map = {f.path: f.content for f in files}
        
        # 2. Commit Files
        # Ensure we have project_id and branch_name set (prepare_workspace should have been called)
        if not self.project_id or not self.branch_name:
             raise ValueError("Workspace not prepared. project_id or branch_name missing.")

        self.gateway.commit_files(self.project_id, self.branch_name, files_map, f"feat: {message}")
        
        # 3. Create Merge Request
        mr_result = self.gateway.create_merge_request(
            project_id=self.project_id,
            source_branch=self.branch_name,
            target_branch="main",
            title=message,
            description=f"Automated scaffolding.\n\n{message}"
        )
        
        # 4. Return URL
        return mr_result.get("web_url", "URL_NOT_FOUND")

class ReporterAgentAdapter(ReporterAgent):
    def __init__(self, gateway: TaskTrackerGatewayPort):
        self.gateway = gateway

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
