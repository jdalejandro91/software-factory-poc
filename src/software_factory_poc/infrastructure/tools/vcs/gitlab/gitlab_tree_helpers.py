"""Pure functions for filtering and formatting GitLab repository tree entries."""

EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        ".tox",
        ".eggs",
        ".pytest_cache",
        ".idea",
        ".vscode",
    }
)

EXCLUDED_EXTS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".jar",
        ".war",
        ".class",
        ".pyc",
        ".so",
        ".dll",
        ".exe",
        ".bin",
        ".lock",
        ".map",
    }
)

MAX_BRANCH_FILES: int = 50


def filter_relevant_paths(entries: list[dict[str, str]]) -> list[str]:
    """Exclude binary files and irrelevant directories."""
    paths: list[str] = []
    for entry in entries:
        path = entry.get("path", "")
        if any(seg in EXCLUDED_DIRS for seg in path.split("/")):
            continue
        if any(path.endswith(ext) for ext in EXCLUDED_EXTS):
            continue
        paths.append(path)
    return paths[:MAX_BRANCH_FILES]


def build_tree_string(paths: list[str]) -> str:
    """Format a flat list of file paths into an indented directory skeleton."""
    if not paths:
        return "(empty repository)"
    lines: list[str] = []
    for path in sorted(paths):
        depth = path.count("/")
        name = path.rsplit("/", 1)[-1]
        lines.append(f"{'  ' * depth}{name}")
    return "\n".join(lines)
