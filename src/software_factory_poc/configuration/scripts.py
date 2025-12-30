import subprocess
import sys


def test():
    """Run tests using pytest."""
    cmd = ["pytest", "tests"]
    sys.exit(subprocess.call(cmd))

def lint():
    """Run linting checks."""
    print("Running ruff check...")
    rc = subprocess.call(["ruff", "check", "."])
    if rc != 0:
        sys.exit(rc)
    
    print("Running ruff format --check...")
    sys.exit(subprocess.call(["ruff", "format", "--check", "."]))

def format():
    """Run formatter."""
    print("Running ruff format...")
    sys.exit(subprocess.call(["ruff", "format", "."]))
