import uuid
from typing import Optional

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.artifact_result_model import (
    ArtifactResultModel,
    ArtifactRunStatusEnum,
)
from software_factory_poc.contracts.scaffolding_contract_parser_service import (
    ContractParseError,
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
    PolicyViolationError,
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
from software_factory_poc.templates.template_file_loader_service import (
    TemplateFileLoaderService,
)
from software_factory_poc.templates.template_registry_service import (
    TemplateRegistryService,
)
from software_factory_poc.templates.template_renderer_service import (
    TemplateRendererService,
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
        template_registry: TemplateRegistryService,
        template_loader: TemplateFileLoaderService,
        template_renderer: TemplateRendererService,
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
        self.template_registry = template_registry
        self.template_loader = template_loader
        self.template_renderer = template_renderer
        self.policy_service = policy_service
        self.gitlab_client = gitlab_client
        self.idempotency_builder = idempotency_builder
        self.idempotency_store = idempotency_store
        self.run_result_store = run_result_store

    def execute(self, issue_key: str) -> ArtifactResultModel:
        """
        Orchestrates the scaffolding flow for a given Jira issue.
        """
        run_id = str(uuid.uuid4())
        logger.info(f"Starting orchestration for issue={issue_key}, run_id={run_id}")

        result_model = ArtifactResultModel(
            run_id=run_id,
            status=ArtifactRunStatusEnum.FAILED,
            issue_key=issue_key,
        )

        try:
            # 1. Get Jira Issue
            jira_issue = self.step_runner.run_step(
                "fetch_jira_issue",
                lambda: self.jira_mapper.map_issue(self.jira_client.get_issue(issue_key)),
                run_id,
                issue_key
            )

            # 2. Parse Contract
            contract = self.step_runner.run_step(
                "parse_contract",
                lambda: self.contract_parser.parse(jira_issue.description),
                run_id,
                issue_key
            )

            # 2.5 Resolve GitLab Project ID if needed
            if not contract.gitlab.project_id and contract.gitlab.project_path:
                resolved_id = self.step_runner.run_step(
                    "resolve_project_id",
                    lambda: self.gitlab_client.resolve_project_id(contract.gitlab.project_path),
                    run_id,
                    issue_key
                )
                contract.gitlab.project_id = resolved_id
            
            # Ensure we have an ID now (model validation ensures one of them was present, 
            # and if it was path, we resolved it. If resolution failed, it raised exception).
            if not contract.gitlab.project_id:
                raise ValueError("Could not resolve a valid GitLab Project ID.")

            # 3. Load Manifest & Render
            # We need manifest first for idempotency and policy
            template_dir = self.template_registry.resolve_template_dir(contract.template_id)
            manifest = self.template_loader.load_manifest(template_dir)

            # 4. Idempotency Check
            idem_key = self.idempotency_builder.build(
                issue_key, contract.contract_version, manifest.template_version
            )
            
            existing_mr = self.idempotency_store.get(idem_key)
            if existing_mr:
                logger.info(f"Duplicate request detected for key {idem_key}")
                self.jira_client.add_comment(
                    issue_key, 
                    f"**DUPLICATE SCAFFOLDING REQUEST DETECTED**\n\nResult already exists: {existing_mr}\nRun ID: {run_id}"
                )
                result_model.status = ArtifactRunStatusEnum.DUPLICATE
                result_model.mr_url = existing_mr
                self.run_result_store.put(run_id, result_model)
                return result_model

            # Render Template
            files_map = self.step_runner.run_step(
                "render_template",
                lambda: self.template_renderer.render(contract.template_id, contract.vars),
                run_id,
                issue_key
            )

            # 5. Policy Validation
            branch_slug = slugify_for_branch(f"{issue_key}-{contract.service_slug}")
            generated_branch_name = f"scaffold/{branch_slug}"

            self.step_runner.run_step(
                "validate_policy",
                lambda: self.policy_service.validate_request(contract, manifest, generated_branch_name),
                run_id,
                issue_key
            )

            # 6. GitLab Operations (Branch, Commit, MR)
            def gitlab_ops():
                # Get base branch from contract or default
                target_base = contract.gitlab.target_base_branch or self.settings.default_target_base_branch
                
                # Create Branch
                self.gitlab_client.create_branch(
                    contract.gitlab.project_id, 
                    generated_branch_name, 
                    target_base
                )
                
                # Commit Files
                self.gitlab_client.commit_files(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    files_map,
                    f"Scaffold {contract.service_slug} from {contract.template_id} (Jira: {issue_key})"
                )
                
                # Create MR
                mr_payload = self.gitlab_client.create_merge_request(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    target_base,
                    f"Scaffold: {contract.service_slug}",
                    f"Scaffolding generated from Jira Issue {issue_key}\nTemplate: {contract.template_id}\nRun ID: {run_id}"
                )
                # We can use the result mapper here if we want strict typing
                from software_factory_poc.integrations.gitlab.gitlab_result_mapper_service import GitLabResultMapperService
                mapper = GitLabResultMapperService()
                return mapper.map_mr(mr_payload)

            mr_data = self.step_runner.run_step(
                "gitlab_operations",
                gitlab_ops,
                run_id,
                issue_key
            )

            result_model.mr_url = mr_data.mr_url
            result_model.branch_name = generated_branch_name
            result_model.status = ArtifactRunStatusEnum.COMPLETED

            # 7. Notify Jira Success
            comment_resp = self.step_runner.run_step(
                "notify_jira_success",
                lambda: self.jira_client.add_comment(
                    issue_key,
                    f"h2. Scaffolding Success :rocket:\n\n"
                    f"**Merge Request**: [{mr_data.mr_url}]\n"
                    f"**Branch**: {generated_branch_name}\n"
                    f"**Run ID**: {run_id}"
                ),
                run_id,
                issue_key
            )
            
            # 8. Persistence
            self.idempotency_store.put(idem_key, mr_data.mr_url)
            self.run_result_store.put(run_id, result_model)
            
            return result_model

        except StepExecutionError as e:
            # Unwrap the original exception for specific handling
            cause = e.original_error
            
            if isinstance(cause, ContractParseError):
                msg = f"**SCAFFOLDING FAILED (Validation Error)**\n\n{str(cause)}"
                self._handle_failure(run_id, issue_key, msg, cause)
                result_model.status = ArtifactRunStatusEnum.FAILED
                result_model.error_summary = str(cause)
                self.run_result_store.put(run_id, result_model)
                return result_model

            elif isinstance(cause, PolicyViolationError):
                msg = f"**SCAFFOLDING FAILED (Policy Violation)**\n\n{str(cause)}"
                self._handle_failure(run_id, issue_key, msg, cause)
                result_model.status = ArtifactRunStatusEnum.FAILED
                result_model.error_summary = str(cause)
                self.run_result_store.put(run_id, result_model)
                return result_model
                
            else:
                # Unexpected inner error
                logger.exception("Unexpected error in orchestration step")
                msg = f"**SCAFFOLDING FAILED (System Error)**\n\nAn unexpected error occurred during processing.\nRun ID: {run_id}"
                self._handle_failure(run_id, issue_key, msg, cause)
                result_model.status = ArtifactRunStatusEnum.FAILED
                result_model.error_summary = f"Internal System Error: {str(cause)}" 
                self.run_result_store.put(run_id, result_model)
                return result_model

        except Exception as e:
            # Catch-all for errors outside of steps (should be rare)
            logger.exception("Unexpected error in orchestration")
            msg = f"**SCAFFOLDING FAILED (System Error)**\n\nAn unexpected error occurred during processing.\nRun ID: {run_id}"
            self._handle_failure(run_id, issue_key, msg, e)
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = "Internal System Error" 
            self.run_result_store.put(run_id, result_model)
            return result_model

    def _handle_failure(self, run_id: str, issue_key: str, user_message: str, exc: Exception):
        """
        Notification of failure to Jira.
        Swallows errors during notification to avoid losing the original error.
        """
        try:
            self.jira_client.add_comment(issue_key, user_message)
        except Exception as notify_err:
            logger.error(f"Failed to post failure comment to Jira for run {run_id}: {notify_err}")
