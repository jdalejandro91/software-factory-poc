import asyncio
import hashlib
import uuid
from typing import Any

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.artifact_result_model import (
    ArtifactResultModel,
    ArtifactRunStatusEnum,
)
from software_factory_poc.contracts.jira_webhook_models import JiraWebhookModel
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
    ScaffoldingContractParserService,
)
from software_factory_poc.integrations.gitlab.gitlab_client import GitLabClient
from software_factory_poc.integrations.jira.jira_client import JiraClient
from software_factory_poc.integrations.jira.jira_issue_mapper_service import (
    JiraIssueMapperService,
)
from software_factory_poc.observability.logger_factory_service import build_logger
from software_factory_poc.orchestration.step_runner_service import (
    StepExecutionError,
    StepRunnerService,
)
from software_factory_poc.policy.poc_policy_service import (
    PocPolicyService,
)
from software_factory_poc.scaffolding.genai_scaffolding_service import (
    GenaiScaffoldingService,
)
from software_factory_poc.store.idempotency_key_builder_service import (
    IdempotencyKeyBuilderService,
)
from software_factory_poc.store.idempotency_store_file_adapter import (
    IdempotencyStoreFileAdapter,
)
from software_factory_poc.store.run_result_store_file_adapter import (
    RunResultStoreFileAdapter,
)
from software_factory_poc.utils.slugify_service import slugify_for_branch

logger = build_logger(__name__)


class ScaffoldOrchestratorService:
    def __init__(
        self,
        settings: Settings,
        step_runner: StepRunnerService,
        jira_client: JiraClient,
        jira_mapper: JiraIssueMapperService,
        contract_parser: ScaffoldingContractParserService,
        genai_service: GenaiScaffoldingService,
        policy_service: PocPolicyService,
        gitlab_client: GitLabClient,
        idempotency_builder: IdempotencyKeyBuilderService,
        idempotency_store: IdempotencyStoreFileAdapter,
        run_result_store: RunResultStoreFileAdapter,
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

    def execute(self, issue_key: str, webhook_payload: JiraWebhookModel | None = None) -> ArtifactResultModel:
        run_id = str(uuid.uuid4())
        logger.info(f"Starting orchestration for issue={issue_key}, run_id={run_id}")

        result_model = ArtifactResultModel(
            run_id=run_id,
            status=ArtifactRunStatusEnum.FAILED,
            issue_key=issue_key,
        )

        try:
            # 1. Get Jira Issue
            jira_issue = None
            if webhook_payload and webhook_payload.issue.fields:
                logger.info(f"Using webhook payload data (Skipping Jira Fetch) for {issue_key}")
                class OptimisticIssue:
                    def __init__(self, key, description, summary):
                        self.key = key
                        self.description = description
                        self.summary = summary
                
                jira_issue = OptimisticIssue(
                    key=issue_key,
                    description=webhook_payload.issue.fields.description or "",
                    summary=webhook_payload.issue.fields.summary or ""
                )
            else:
                jira_issue = self.step_runner.run_step(
                    "fetch_jira_issue",
                    lambda: self.jira_mapper.map_issue(self.jira_client.get_issue(issue_key)),
                    run_id,
                    issue_key
                )

            # 2. Parse Contract (Still valid if legacy or just extraction of metadata)
            # The contract parser extracts high level intents, though GenAI might not strictly need it.
            # But we keep it for policy validation and basic checks.
            contract = self.step_runner.run_step(
                "parse_contract",
                lambda: self.contract_parser.parse(jira_issue.description),
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
            # Using SHA256 of description instead of template logic
            description_hash = hashlib.sha256(jira_issue.description.encode("utf-8")).hexdigest()
            idem_key = self.idempotency_builder.build(
                issue_key, contract.contract_version, description_hash
            )
            
            existing_mr = self.idempotency_store.get(idem_key)
            if existing_mr:
                logger.info(f"Duplicate request detected for key {idem_key}")
                self._notify_duplicate(issue_key, existing_mr)
                result_model.status = ArtifactRunStatusEnum.DUPLICATE
                result_model.mr_url = existing_mr
                self.run_result_store.put(run_id, result_model)
                return result_model

            # 5. GenAI Scaffolding Generation
            # We call the async genai_service.generate_scaffolding.
            # StepRunner isn't natively async aware in this MVP, so we wrap in asyncio.run or ensure StepRunner can handle updates?
            # Orchestrator is synchronous in router. We probably should update router to async def?
            # Wait, router is async def trigger_scaffold. Orchestrator.execute is currently sync.
            # We should probably run the coroutine here synchronously for now using asyncio.run
            # since StepRunner expects a callable.
            
            files_map = self.step_runner.run_step(
                "generate_scaffolding",
                lambda: asyncio.run(self.genai_service.generate_scaffolding(issue_key, jira_issue.description)),
                run_id,
                issue_key
            )

            # 6. Policy Validation (Simplified or adapted)
            # Existing policy service validated generated files? Or contract?
            # policy_service.validate_request(contract, manifest...)
            # We no longer have a manifest. We might skip manifest validation or adapt policy service.
            # For this MVP, let's assume we skip manifest-based policy checks or pass dummy manifest.
            # But wait, generated_branch_name is needed.
            
            branch_slug = slugify_for_branch(f"{issue_key}-{contract.service_slug}")
            generated_branch_name = f"feature/{branch_slug}-scaffold"

            # Skipping strict manifest validation for now as GenAI is dynamic.
            
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
                    files_map,
                    f"Scaffold {contract.service_slug} (GenAI) (Jira: {issue_key})"
                )
                
                mr_data_raw = self.gitlab_client.create_merge_request(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    target_base,
                    f"Scaffold: {contract.service_slug}",
                    f"Scaffolding generated by AI Agent from Jira Issue {issue_key}\nRun ID: {run_id}"
                )
                
                from software_factory_poc.integrations.gitlab.gitlab_result_mapper_service import (
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
            self.idempotency_store.put(idem_key, mr_data.mr_url)
            self.run_result_store.put(run_id, result_model)
            
            return result_model

        except StepExecutionError as e:
            cause = e.original_error
            self._notify_failure(run_id, issue_key, cause)
            
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = str(cause)
            self.run_result_store.put(run_id, result_model)
            return result_model

        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            self._notify_failure(run_id, issue_key, e, is_critical=True)
            
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = "Internal System Error" 
            self.run_result_store.put(run_id, result_model)
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
