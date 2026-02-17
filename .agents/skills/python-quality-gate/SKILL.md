---
name: python-quality-gate
description: Acts as a SonarQube equivalent. Installs, configures, and enforces ultra-strict code quality using Ruff, Mypy, and Vulture. Use to setup linters, fix cyclomatic complexity, or hunt dead code, unused methods, and orphan classes.
---
# Python Quality Gate Skill (SonarQube Alternative)

## When to use this skill
- When bootstrapping or refining the project's quality configuration (`pyproject.toml`, `ruff.toml`).
- When fixing violations reported by the Execution Protocols (Ruff, Mypy, Vulture).

## The Quality Trinity Setup
Check `pyproject.toml` or `requirements.txt`. If `ruff`, `mypy`, or `vulture` are missing from the dev dependencies, install them immediately (e.g., `uv add --dev ruff mypy vulture`).

### 1. Ruff (Linter, Formatter & Code Smells)
Check `pyproject.toml` (under `[tool.ruff]`). If it exists, REFINE it; if not, CREATE it. Enforce an ULTRA-STRICT configuration:
- **Enable these rule prefixes in `select`:** 
  `["E", "F", "W", "I", "N", "B", "C90", "SIM", "ARG", "PL", "ERA", "RUF"]`
- **What this checks:** 
  - `F`: Unused imports/variables.
  - `C90`: McCabe Complexity. Enforce `[tool.ruff.lint.mccabe] max-complexity = 8` to prevent spaghetti code.
  - `PL`: Pylint (duplicated code, bad design).
  - `ARG`: Unused function arguments.
  - `ERA`: Eradicate (Commented-out zombie code).
- **Action**: If Ruff complains about complexity (`C901`), apply the Composed Method pattern (extract logic into smaller private methods). If it finds commented code (`ERA001`), DELETE IT. We use Git for history.

### 2. Vulture (Dead Code Exterminator)
Vulture specifically finds unused methods, classes, and properties globally across the project.
- **Configuration**: Add this to `pyproject.toml`:
  ```toml
  [tool.vulture]
  min_confidence = 80
  paths = ["src/"]
  ```
- **Action**: When Vulture reports unused code, DO NOT ignore it. Verify it is not a dynamically loaded entrypoint (like a FastAPI router). If it is genuinely dead code left over from a refactor, DELETE IT COMPLETELY.

### 3. Mypy (Strict Typing)
Check pyproject.toml or mypy.ini. Refine to ensure strict enforcement:
strict = true
disallow_untyped_defs = true
warn_unused_ignores = true