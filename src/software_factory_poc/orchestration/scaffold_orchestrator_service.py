import uuid
from typing import Optional, Dict, Any

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
from software_factory_poc.contracts.jira_webhook_models import JiraWebhookModel

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

    def execute(self, issue_key: str, webhook_payload: Optional[JiraWebhookModel] = None) -> ArtifactResultModel:
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

            # 2. Parse Contract
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

            # 3. Load Manifest & Render
            template_dir = self.template_registry.resolve_template_dir(contract.template_id)
            manifest = self.template_loader.load_manifest(template_dir)

            # 4. Idempotency Check
            idem_key = self.idempotency_builder.build(
                issue_key, contract.contract_version, manifest.template_version
            )
            
            existing_mr = self.idempotency_store.get(idem_key)
            if existing_mr:
                logger.info(f"Duplicate request detected for key {idem_key}")
                
                adf_duplicate = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "panel",
                            "attrs": {"panelType": "warning"},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Duplicate Request Detected", "marks": [{"type": "strong"}]}
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "This scaffolding has already been executed. "},
                                        {"type": "text", "text": "View Existing MR", "marks": [{"type": "link", "attrs": {"href": existing_mr}}]}
                                    ]
                                }
                            ]
                        }
                    ]
                }

                try:
                    self.jira_client.add_comment(issue_key, adf_duplicate)
                except Exception:
                    logger.warning("Failed to post duplicate comment")

                result_model.status = ArtifactRunStatusEnum.DUPLICATE
                result_model.mr_url = existing_mr
                self.run_result_store.put(run_id, result_model)
                return result_model

            # Render
            files_map = self.step_runner.run_step(
                "render_template",
                lambda: self.template_renderer.render(contract.template_id, contract.vars),
                run_id,
                issue_key
            )

            # 5. Policy Validation
            branch_slug = slugify_for_branch(f"{issue_key}-{contract.service_slug}")
            generated_branch_name = f"feature/{branch_slug}-scaffold"

            self.step_runner.run_step(
                "validate_policy",
                lambda: self.policy_service.validate_request(contract, manifest, generated_branch_name),
                run_id,
                issue_key
            )

            # 6. GitLab Operations
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
                    f"Scaffold {contract.service_slug} from {contract.template_id} (Jira: {issue_key})"
                )
                
                mr_data_raw = self.gitlab_client.create_merge_request(
                    contract.gitlab.project_id,
                    generated_branch_name,
                    target_base,
                    f"Scaffold: {contract.service_slug}",
                    f"Scaffolding generated from Jira Issue {issue_key}\nTemplate: {contract.template_id}\nRun ID: {run_id}"
                )
                
                from software_factory_poc.integrations.gitlab.gitlab_result_mapper_service import GitLabResultMapperService
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

            # 7. Notify Jira Success
            try:
                adf_success_body = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "panel",
                            "attrs": {"panelType": "success"},
                            "content": [
                                {
                                    "type": "heading",
                                    "attrs": {"level": 3},
                                    "content": [{"type": "text", "text": "Scaffolding Success 🚀"}]
                                }
                            ]
                        },
                        {
                            "type": "bulletList",
                            "content": [
                                {
                                    "type": "listItem",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "Merge Request: ", "marks": [{"type": "strong"}]},
                                                {
                                                    "type": "text", 
                                                    "text": mr_data.mr_url, 
                                                    "marks": [{"type": "link", "attrs": {"href": mr_data.mr_url}}]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "listItem",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "Branch: ", "marks": [{"type": "strong"}]},
                                                {
                                                    "type": "text", 
                                                    "text": generated_branch_name, 
                                                    "marks": [
                                                        {"type": "code"},
                                                        {"type": "link", "attrs": {"href": branch_url or ""}}
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "listItem",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {"type": "text", "text": "Run ID: ", "marks": [{"type": "strong"}]},
                                                {"type": "text", "text": run_id, "marks": [{"type": "code"}]}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }

                self.step_runner.run_step(
                    "notify_jira_success",
                    lambda: self.jira_client.add_comment(issue_key, adf_success_body),
                    run_id,
                    issue_key
                )
            except Exception:
                logger.warning("Failed to post success comment")

            # 9. Transition Issue to Review (Success Path)
            try:
                def do_transition_success():
                    if not self.jira_client.transition_issue(issue_key, "revisión"):
                        self.jira_client.transition_issue(issue_key, "review")

                self.step_runner.run_step(
                    "transition_issue_success",
                    do_transition_success,
                    run_id,
                    issue_key
                )
            except Exception:
                logger.warning("Failed to transition issue state (ignoring as non-critical)")
            
            # 8. Persistence
            self.idempotency_store.put(idem_key, mr_data.mr_url)
            self.run_result_store.put(run_id, result_model)
            
            return result_model

        except StepExecutionError as e:
            cause = e.original_error
            
            error_title = "Scaffolding Failed"
            if isinstance(cause, ContractParseError):
                error_title = "Validation Error"
            elif isinstance(cause, PolicyViolationError):
                error_title = "Policy Violation"
            
            adf_error = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "panel",
                        "attrs": {"panelType": "error"},
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 3},
                                "content": [{"type": "text", "text": error_title}]
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": str(cause)}]
                            },
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Run ID: "},
                                    {"type": "text", "text": run_id, "marks": [{"type": "code"}]}
                                ]
                            }
                        ]
                    }
                ]
            }

            self._handle_failure(run_id, issue_key, adf_error, cause)
            
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = str(cause)
            self.run_result_store.put(run_id, result_model)
            return result_model

        except Exception as e:
            logger.exception("Unexpected error in orchestration")
            
            adf_critical = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "panel",
                        "attrs": {"panelType": "error"},
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 3},
                                "content": [{"type": "text", "text": "Critical System Error"}]
                            },
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "An unexpected error occurred. Please check system logs."}]
                            },
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Run ID: "},
                                    {"type": "text", "text": run_id, "marks": [{"type": "code"}]}
                                ]
                            }
                        ]
                    }
                ]
            }
            
            self._handle_failure(run_id, issue_key, adf_critical, e)
            result_model.status = ArtifactRunStatusEnum.FAILED
            result_model.error_summary = "Internal System Error" 
            self.run_result_store.put(run_id, result_model)
            return result_model

    def _handle_failure(self, run_id: str, issue_key: str, message_payload: Dict[str, Any], exc: Exception):
        """
        Notifica el fallo a Jira y revierte el estado de la tarea.
        """
        # 1. Comentar el error
        try:
            self.jira_client.add_comment(issue_key, message_payload)
        except Exception as notify_err:
            logger.error(f"Failed to post failure comment to Jira for run {run_id}: {notify_err}")

        # 2. Revertir estado a "To Do" / "Por hacer"
        try:
            logger.info(f"Attempting to rollback issue {issue_key} to initial state due to failure.")
            # Intentamos encontrar una transición hacia el estado inicial
            # Si tu Jira está en Español, el estado suele ser "Tareas por hacer" (o la transición "Detener").
            # Si está en Inglés, "To Do".
            # Buscamos por palabras clave comunes.
            if not self.jira_client.transition_issue(issue_key, "hacer"): # Cubre "Tareas por hacer", "Por hacer"
                 self.jira_client.transition_issue(issue_key, "To Do") # Cubre "To Do"
        except Exception as trans_err:
            logger.error(f"Failed to rollback issue state to To Do for run {run_id}: {trans_err}")
