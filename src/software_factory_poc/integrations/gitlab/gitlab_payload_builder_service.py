from typing import Any, Dict, List

class GitLabPayloadBuilderService:
    def build_commit_payload(
        self, 
        files_map: Dict[str, str], 
        branch_name: str, 
        message: str,
        files_action_map: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Builds the JSON payload for the GitLab Commits API.
        Transforms files_map {path: content} into actions list.
        :param files_action_map: Optional dict mapping file_path -> "create"|"update"
        """
        actions: List[Dict[str, str]] = []
        files_action_map = files_action_map or {}
        
        for file_path, content in files_map.items():
            self._validate_path(file_path)
            
            # Default to 'create' if not specified
            action_type = files_action_map.get(file_path, "create")
            
            action = {
                "action": action_type,
                "file_path": file_path,
                "content": content,
            }
            actions.append(action)
            
        return {
            "branch": branch_name,
            "commit_message": message,
            "actions": actions
        }

    def _validate_path(self, path: str):
        if not path:
            raise ValueError("File path cannot be empty")
        # Check for directory traversal
        if ".." in path:
            raise ValueError(f"Path contains invalid sequence '..': {path}")
        # Check for absolute path (leading slash is usually fine in gitlab but we prefer relative to root)
        # Gitlab API expects file_path relative to repository root.
        # It's cleaner to remove leading slash if present or error.
        if path.startswith("/"):
            raise ValueError(f"Path must be relative (no leading slash): {path}")
        if "\\" in path:
            raise ValueError(f"Path must use POSIX separators (/): {path}")
