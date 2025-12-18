from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.scaffolding_contract_model import ScaffoldingContractModel
from software_factory_poc.templates.template_manifest_model import TemplateManifestModel


class PolicyViolationError(Exception):
    """Raised when a request violates a policy."""
    pass


class PocPolicyService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def validate_request(
        self, 
        contract: ScaffoldingContractModel,
        manifest: TemplateManifestModel,
        generated_branch_name: str
    ):
        """
        Validates the request against the configured policies (allowlists, protected branches).
        """
        # 1. Validate Template Allowlisting
        if contract.template_id not in self.settings.allowlisted_template_ids:
            raise PolicyViolationError(f"Template '{contract.template_id}' is not in the allowlist.")

        # 2. Validate GitLab Project Allowlisting
        if contract.gitlab.project_id not in self.settings.allowlisted_gitlab_project_ids:
            raise PolicyViolationError(f"GitLab Project ID '{contract.gitlab.project_id}' is not in the allowlist.")

        # 3. Validate target base branch (Optional in MVP, usually we want to ensure base exists, 
        # but policy-wise, we might block branching FROM restricted branches if configured. 
        # Here we only check if defaults match. 
        # The prompt asks: "allow target main, but prohibit writes directos; aqui solo MR, asi que ok"
        # So no specific check on TARGET base branch required other than general sane-ness.)
        
        # 4. Validate Generated Branch Name (The HEAD branch)
        # Cannot overwrite protected branches
        if generated_branch_name in self.settings.protected_branches:
            raise PolicyViolationError(f"Generated branch name '{generated_branch_name}' conflicts with a protected branch.")

        # 5. Manifest sanity checks (redundant but safe)
        # Ensure we aren't using a template that claims to write to restricted paths if we had path policies.
        # But 'renderer' controls scope largely.
        
        # Success
        return
