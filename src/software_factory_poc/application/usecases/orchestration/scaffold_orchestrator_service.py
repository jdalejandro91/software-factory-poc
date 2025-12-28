import asyncio
import hashlib
import uuid
from typing import Any

from software_factory_poc.application.core.entities.idempotency_record import IdempotencyRecord
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.ports.memory.repository import Repository
from software_factory_poc.application.ports.tools.gitlab_provider import GitLabProvider
from software_factory_poc.application.ports.tools.jira_provider import JiraProvider
from software_factory_poc.application.usecases.scaffolding.genai_scaffolding_service import (
    GenaiScaffoldingService,
)
from software_factory_poc.configuration.main_settings import Settings
from software_factory_poc.application.core.entities.artifact_result import (
    ArtifactResultModel,
    ArtifactRunStatusEnum,
)
from software_factory_poc.application.core.services.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
)

from software_factory_poc.infrastructure.providers.tools.jira.mappers.jira_issue_mapper_service import (
    JiraIssueMapperService,
)
from software_factory_poc.infrastructure.repositories.idempotency_key_builder_service import (
    IdempotencyKeyBuilderService,
)
from software_factory_poc.observability.logger_factory_service import build_logger
from software_factory_poc.orchestration.step_runner_service import (
    StepExecutionError,
    StepRunnerService,
)
from software_factory_poc.policy.poc_policy_service import (
    PocPolicyService,
)
from software_factory_poc.utils.slugify_service import slugify_for_branch

logger = build_logger(__name__)


class ScaffoldOrchestratorService:
    def __init__(
        self,
        settings: Settings,
        step_runner: StepRunnerService,
        jira_client: JiraProvider,
        jira_mapper: JiraIssueMapperService,
        contract_parser: ScaffoldingContractParserService,
        genai_service: GenaiScaffoldingService,
        policy_service: PocPolicyService,
        gitlab_client: GitLabProvider,
        idempotency_builder: IdempotencyKeyBuilderService,
        idempotency_store: Repository[IdempotencyRecord],
        run_result_store: Repository[ArtifactResultModel],
    ):
        self.settings = settings
        self.step_runner = step_runner
        self.jira_client = jira_client
        self.jira_mapper = jira_mapper
        self.contract_parser = contract_parser
        self.genai_service = genai_service
        self.policy_service = policy_service
        self.gitlab_client = gitlab_client
        self.idempotency_builder = idempotency_builder
        self.idempotency_store = idempotency_store
        self.run_result_store = run_result_store

    def execute(self, request: ScaffoldingRequest) -> ArtifactResultModel:
        issue_key = request.ticket_id
        run_id = str(uuid.uuid4())
        logger.info(f"Starting orchestration for issue={issue_key}, run_id={run_id}")

        result_model = ArtifactResultModel(
            run_id=run_id,
            status=ArtifactRunStatusEnum.FAILED,
            issue_key=issue_key,
        )

        try:
            # 1. Parse Contract (from request instruction)
            # No need to fetch Jira issue as we trust the request data (Optimistic)
            contract = self.step_runner.run_step(
                "parse_contract",
                lambda: self.contract_parser.parse(request.raw_instruction),
                run_id,
                issue_key
            )

            # 2.5 Resolve GitLab Project ID
            if not contract.gitlab.project_id and contract.gitlab.project_path:
                resolved_id = self.step_runner.run_step(
                    "resolve_project_id",
                    lambda: self.gitlab_client.resolve_project_id(contract.gitlab.project_path),
                    run_id,
                    issue_key
                )
                contract.gitlab.project_id = resolved_id
            
            if not contract.gitlab.project_id:
                raise ValueError("Could not resolve a valid GitLab Project ID.")

            # 4. Idempotency Check
            # Using SHA256 of raw_instruction
            description_hash = hashlib.sha256(request.raw_instruction.encode("utf-8")).hexdigest()
            idem_key = self.idempotency_builder.build(
                issue_key, contract.contract_version, description_hash
            )
            
            existing_record = self.idempotency_store.find_by_id(idem_key)
            if existing_record:
                existing_mr = existing_record.mr_url
                logger.info(f"Duplicate request detected for key {idem_key}")
                self._notify_duplicate(issue_key, existing_mr)
                result_model.status = ArtifactRunStatusEnum.DUPLICATE
                result_model.mr_url = existing_mr
                self.run_result_store.save(result_model)
                return result_model

            # 5. GenAI Scaffolding Generation
            # We pass raw_instruction as context? Or full description?
            # GenAI might need full context? User said "raw_instruction (el contenido del bloque)".
            # If user puts helpful info outside the block, it is lost?
            # For now, sticking to raw_instruction as "description" passed to GenAI?
            # GenAI service signature: `generate_scaffolding(issue_key, description)`.
            # I will pass `request.raw_instruction` (or maybe `request.summary` + `request.raw_instruction`?)
            # I'll pass `request.raw_instruction` as the description/prompt context.

            files_map = self.step_runner.run_step(
                "generate_scaffolding",
                lambda: asyncio.run(self.genai_service.generate_scaffolding(issue_key, request.raw_instruction)),
                run_id,
                issue_key
            )

            # 6. Policy Validation (Simplified)
            branch_slug = slugify_for_branch(f"{issue_key}-{contract.service_slug}")
            generated_branch_name = f"feature/{branch_slug}-scaffold"

            # 7. GitLab Operations
            def gitlab_ops():
                target_base = contract.gitlab.target_base_branch or self.settings.default_target_base_branch
                
                branch_resp = self.gitlab_client.create_branch(
                    contract.gitlab.project_id, 
                    generated_branch_name, 
                    target_base
                )
                branch_url = branch_resp.get("web_url")
                
                self.gitlab_client.commit_files(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    files_map, # Note: args swapped in Provider Interface in previous step
                    f"Scaffold {contract.service_slug} (GenAI) (Jira: {issue_key})"
                )
                
                mr_data_raw = self.gitlab_client.create_merge_request(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    target_base,
                    f"Scaffold: {contract.service_slug}",
                    f"Scaffolding generated by AI Agent from Jira Issue {issue_key}\nRun ID: {run_id}"
                )
                
                from software_factory_poc.infrastructure.providers.tools.gitlab.mappers.gitlab_result_mapper_service import (
                    GitLabResultMapperService,
                )
                mapper = GitLabResultMapperService()
                
                return {
                    "mr": mapper.map_mr(mr_data_raw),
                    "branch_url": branch_url
                }

            ops_result = self.step_runner.run_step(
                "gitlab_operations",
                gitlab_ops,
                run_id,
                issue_key
            )
            
            mr_data = ops_result["mr"]
            branch_url = ops_result["branch_url"]

            result_model.mr_url = mr_data.mr_url
            result_model.branch_name = generated_branch_name
            result_model.status = ArtifactRunStatusEnum.COMPLETED

            # 8. Notify Jira Success
            self._notify_success(issue_key, run_id, mr_data.mr_url, generated_branch_name, branch_url)

            # 9. Transition Issue to Review
            self._transition_to_review(issue_key, run_id)
            
            # 10. Persistence
            self.idempotency_store.save(IdempotencyRecord(key=idem_key, mr_url=mr_data.mr_url))
            self.run_result_store.save(result_model)
            
            return result_model

        except StepExecutionError as e:
            cause = e.original_error
            self._notify_failure(run_id, issue_key, cause)
            
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = str(cause)
            self.run_result_store.save(result_model)
            return result_model

        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            self._notify_failure(run_id, issue_key, e, is_critical=True)
            
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = "Internal System Error" 
            self.run_result_store.save(result_model)
            return result_model

    def _notify_duplicate(self, issue_key, existing_mr):
        adf = {
            "type": "doc", "version": 1,
            "content": [{
                "type": "panel", "attrs": {"panelType": "warning"},
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Duplicate Request. MR already exists: "},
                                {"type": "text", "text": existing_mr, "marks": [{"type": "link", "attrs": {"href": existing_mr}}]}]
                }]
            }]
        }
        try:
            self.jira_client.add_comment(issue_key, adf)
        except Exception:
            logger.warning("Failed to post duplicate comment")

    def _notify_success(self, issue_key, run_id, mr_url, branch_name, branch_url):
         # Simplified Success ADF construction
        adf = {
            "type": "doc", "version": 1,
            "content": [
                {"type": "panel", "attrs": {"panelType": "success"}, "content": [{"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "GenAI Scaffolding Success 🚀"}]}]},
                {"type": "bulletList", "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Merge Request: "}, {"type": "text", "text": mr_url, "marks": [{"type": "link", "attrs": {"href": mr_url}}]}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Run ID: "}, {"type": "text", "text": run_id, "marks": [{"type": "code"}]}]}]}
                ]}
            ]
        }
        try:
            self.jira_client.add_comment(issue_key, adf)
        except Exception:
            logger.warning("Failed to post success comment")

    def _notify_failure(self, run_id, issue_key, cause, is_critical=False):
        error_title = "Critical System Error" if is_critical else "Scaffolding Failed"
        adf = {
            "type": "doc", "version": 1,
            "content": [
                {"type": "panel", "attrs": {"panelType": "error"}, "content": [
                    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": error_title}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": str(cause)}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": f"Run ID: {run_id}"}]}
                ]}
            ]
        }
        self._handle_failure(run_id, issue_key, adf, cause)

    def _transition_to_review(self, issue_key, run_id):
        try:
            if not self.jira_client.transition_issue(issue_key, "revisión"):
                self.jira_client.transition_issue(issue_key, "review")
        except Exception:
            logger.warning("Failed to transition issue state")

    def _handle_failure(self, run_id: str, issue_key: str, message_payload: dict[str, Any], exc: Exception):
        try:
            self.jira_client.add_comment(issue_key, message_payload)
        except Exception as notify_err:
            logger.error(f"Failed to post failure comment to Jira for run {run_id}: {notify_err}")

        try:
            logger.info(f"Attempting to rollback issue {issue_key} to initial state due to failure.")
            if not self.jira_client.transition_issue(issue_key, "hacer"): 
                 self.jira_client.transition_issue(issue_key, "To Do") 
        except Exception as trans_err:
            logger.error(f"Failed to rollback issue state to To Do for run {run_id}: {trans_err}")
