# src/software_factory_poc/config/allowlists_config.py

# Defaults for allowlists if not provided via Environment Variables
# The PoC uses these defaults to "simulate" enterprise policy management.

DEFAULT_ALLOWLISTED_TEMPLATE_IDS = [
    "corp_nodejs_api",
    "corp_python_worker",
]

DEFAULT_ALLOWLISTED_GITLAB_PROJECT_IDS = [
    123,
    456,
]

DEFAULT_PROTECTED_BRANCHES = [
    "main",
    "master",
    "production",
    "develop",
]
