import shutil
import os

moves = [
    ("src/software_factory_poc/application/core/domain/exceptions/confluence_error.py", "src/software_factory_poc/application/core/domain/agents/knowledge/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/contract_parse_error.py", "src/software_factory_poc/application/core/domain/agents/scaffolding/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/provider_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/infra_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/domain_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/retryable_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/configuration_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/domain/exceptions/dependency_error.py", "src/software_factory_poc/application/core/domain/agents/common/exceptions/"),
    ("src/software_factory_poc/application/core/shared/dependency_guard.py", "src/software_factory_poc/application/core/domain/agents/common/tools/"),
    ("src/software_factory_poc/application/core/shared/time_service.py", "src/software_factory_poc/application/core/domain/agents/common/tools/")
]

base_path = "/Users/juancadena/projects/software-factory-poc"

for src, dst in moves:
    abs_src = os.path.join(base_path, src)
    abs_dst = os.path.join(base_path, dst)
    
    if os.path.exists(abs_src):
        try:
            shutil.move(abs_src, abs_dst)
            print(f"Moved {src} to {dst}")
        except Exception as e:
            print(f"Error moving {src}: {e}")
    else:
        print(f"Source not found (maybe already moved): {src}")
