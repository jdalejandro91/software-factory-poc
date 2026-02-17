---
name: python-coding
description: Generates and refactors Python 3.12+ code using Object-Oriented Design, SOLID principles, and strict typing. Use when writing new classes, functions, or refactoring Python code.
---
# Python Coding & Clean Code Skill

## When to use this skill
- Use this when writing or refactoring `.py` files.
- This is helpful for ensuring strict typing and SOLID principles.

## How to use it
- **Type Hinting**: Use native Python 3.12 generics (`list[str]`, `dict[str, Any]`). NEVER use `typing.List`. Use `|` for unions (`str | None`). Explicit return types are MANDATORY.
- **Composed Method**: Methods should rarely exceed 15-20 lines. Extract complex logic into private methods. Use early returns (guard clauses) to prevent deep nesting.
- **Dependency Injection**: NEVER instantiate external services or Ports inside an `__init__`. Inject them.

## Decision Tree: What type of object are you building?
- **Domain Object (Entity/Value Object)?**
  - Use `@dataclass(frozen=True, kw_only=True)`. Do not use Pydantic here.
- **DTO crossing an I/O boundary (HTTP/MCP) or Config?**
  - Use `pydantic.BaseModel` (V2).
- **Port (Interface)?**
  - Use `abc.ABC` and `@abstractmethod`. Return only Domain objects.