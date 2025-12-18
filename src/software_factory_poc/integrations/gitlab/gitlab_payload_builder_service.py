from typing import Any, Dict, List

class GitLabPayloadBuilderService:
    def build_commit_payload(
        self, 
        files_map: Dict[str, str], 
        branch_name: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Builds the JSON payload for the GitLab Commits API.
        Transforms files_map {path: content} into actions list.
        """
        actions: List[Dict[str, str]] = []
        
        for file_path, content in files_map.items():
            self._validate_path(file_path)
            
            # For this PoC, we assume all actions are 'create'.
            # A more robust system might check if file exists to choose 'update'.
            # But the PoC contract assumes new files for scaffolding mostly.
            # We'll use 'create'.
            
            action = {
                "action": "create",
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
