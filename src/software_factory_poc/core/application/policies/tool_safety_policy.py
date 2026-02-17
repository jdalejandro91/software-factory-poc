import logging
from typing import Any

logger = logging.getLogger(__name__)

# Actions blocked per agent role.
# Any tool whose function name contains a blocked substring is removed.
_BLOCKED_ACTIONS: dict[str, list[str]] = {
    "Orchestrator": [
        "delete_branch",
        "delete_repository",
        "merge",
        "approve_merge_request",
    ],
    "Reviewer": [
        "delete_branch",
        "delete_repository",
        "create_branch",
        "create_commit",
        "merge",
    ],
}

# Universal blocklist applied to ALL roles.
_UNIVERSAL_BLOCKLIST: list[str] = [
    "delete_project",
    "delete_repository",
    "delete_group",
]


class ToolSafetyPolicy:
    """Filters tools exposed to the LLM based on the agent's role.

    Prevents destructive actions (e.g. delete_branch, merge) from being
    available during agentic loops, enforcing least-privilege per role.
    """

    def filter_allowed_tools(
        self, tools: list[dict[str, Any]], agent_role: str
    ) -> list[dict[str, Any]]:
        """Return only tools that the given role is allowed to invoke."""
        role_blocklist = _BLOCKED_ACTIONS.get(agent_role, [])
        combined_blocklist = role_blocklist + _UNIVERSAL_BLOCKLIST

        allowed: list[dict[str, Any]] = []
        for tool in tools:
            tool_name = tool.get("function", {}).get("name", "")
            if self._is_blocked(tool_name, combined_blocklist):
                logger.info(
                    "[ToolSafetyPolicy] Blocked tool '%s' for role '%s'",
                    tool_name,
                    agent_role,
                )
                continue
            allowed.append(tool)

        return allowed

    @staticmethod
    def _is_blocked(tool_name: str, blocklist: list[str]) -> bool:
        return any(blocked in tool_name for blocked in blocklist)
