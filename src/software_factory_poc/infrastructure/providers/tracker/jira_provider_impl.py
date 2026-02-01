from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus
from software_factory_poc.application.core.agents.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.application.core.agents.reporter.config.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.agents.reporter.ports.task_tracker_gateway import TaskTrackerGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.tracker.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.infrastructure.providers.tracker.dtos.jira_status_enum import JiraStatus

logger = LoggerFactoryService.build_logger(__name__)


# Mapping from Domain Status to Infrastructure (Jira) Status
STATUS_MAPPING = {
    TaskStatus.TO_DO: JiraStatus.TO_DO,
    TaskStatus.IN_PROGRESS: JiraStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW: JiraStatus.IN_REVIEW,
    TaskStatus.DONE: JiraStatus.DONE,
}


from software_factory_poc.infrastructure.configuration.jira_settings import JiraSettings

class JiraProviderImpl(TaskTrackerGateway):
    def __init__(self, http_client: JiraHttpClient, settings: JiraSettings):
        self.client = http_client
        self.settings = settings
        self._logger = logger

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_issue(self, issue_key: str) -> dict[str, Any]:
        self._logger.info(f"Fetching Jira issue: {issue_key}")
        try:
             response = self.client.get(f"rest/api/3/issue/{issue_key}")
             response.raise_for_status()
             return response.json()
        except Exception as e:
             self._handle_error(e, f"get_issue({issue_key})")
             raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def add_comment(self, issue_key: str, body: Any) -> dict[str, Any]:
        self._logger.info(f"Adding comment to Jira issue: {issue_key}")
        try:
            from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory
            payload = JiraPanelFactory.create_payload(body)
            
            self._logger.debug(f"Sending comment payload to Jira: {payload}")
            response = self.client.post(f"rest/api/3/issue/{issue_key}/comment", payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
             self._handle_error(e, f"add_comment({issue_key})")
             raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        self._logger.info(f"Transitioning issue: {issue_key} to state matching: {transition_id}")
        try:
            final_id = self._resolve_transition_id(issue_key, transition_id)
            
            self._logger.info(f"Transitioning issue {issue_key} to (ID: {final_id})")
            payload = {
                "transition": {
                    "id": final_id
                }
            }
            resp = self.client.post(f"rest/api/3/issue/{issue_key}/transitions", payload)
            resp.raise_for_status()
        except Exception as e:
            self._handle_error(e, f"transition_issue({issue_key}, {transition_id})")
            raise

    def _resolve_transition_id(self, issue_key: str, target_keyword: str) -> str:
        """Resolves transition ID from keyword using Exact, then Partial matching."""
        # 1. Fetch available transitions
        response = self.client.get(f"rest/api/3/issue/{issue_key}/transitions")
        try:
            response.raise_for_status()
        except Exception as e:
            self._logger.error(f"Failed to fetch transitions for {issue_key}: {e}")
            raise e
            
        transitions = response.json().get("transitions", [])
        available_names = [t["name"] for t in transitions]
        
        keyword_lower = target_keyword.lower()
        
        # 2a. Exact Match
        for t in transitions:
            if t["name"].lower() == keyword_lower:
                return t["id"]
        
        # 2b. Partial Match
        for t in transitions:
             if keyword_lower in t["name"].lower() or keyword_lower in t["to"]["name"].lower():
                 return t["id"]
                 
        # 3. Not Found
        error_msg = f"Transition '{target_keyword}' not found. Available: {available_names}"
        self._logger.error(error_msg)
        raise ProviderError(
            provider=TaskTrackerType.JIRA,
            message=error_msg,
            retryable=False # Configuration error usually
        )

    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Adapts TaskTrackerGatewayPort.transition_status to internal transition_issue logic."""
        # Configurable override for IN_REVIEW
        if status == TaskStatus.IN_REVIEW:
            transition_name = self.settings.transition_in_review
            self._logger.info(f"Transitioning {task_id} to IN_REVIEW using configured transition: '{transition_name}'")
            self.transition_issue(task_id, transition_name)
            return

        # Translate Domain Status to Infrastructure Status (String) for others
        jira_target_status = STATUS_MAPPING.get(status)
        
        if jira_target_status:
            # Use the specific string value from JiraStatus (e.g., "Por hacer")
            self.transition_issue(task_id, jira_target_status.value)
        else:
            # Fallback: Try to use the value directly if not in mapping (e.g. if TaskStatus matches Jira)
            self._logger.warning(f"No explicit mapping for TaskStatus '{status}'. Using value directly.")
            self.transition_issue(task_id, status.value)

    def _handle_error(self, error: Exception, context: str) -> None:
        """Centralized error handling and logging."""
        self._logger.error(f"Error in JiraProviderImpl [{context}]: {str(error)}", exc_info=True)
        
        if isinstance(error, ProviderError):
            return
            
        msg = str(error)
        retryable = False
        if "500" in msg or "502" in msg or "503" in msg or "504" in msg:
            retryable = True
        elif "Connection" in msg or "Timeout" in msg:
             retryable = True
             
        raise ProviderError(
            provider=TaskTrackerType.JIRA,
            message=f"Jira operation failed: {error}",
            retryable=retryable
        ) from error

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def update_task_description(self, task_id: str, description: str) -> None:
        self._logger.info(f"Updating description for task: {task_id}")
        try:
            # Jira Cloud V3 requires ADF (Atlassian Document Format)
            payload = {
                "fields": {
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }]
                    }
                }
            }
            response = self.client.put(f"rest/api/3/issue/{task_id}", payload)
            response.raise_for_status()
        except Exception as e:
            self._handle_error(e, f"update_task_description({task_id})")
            raise
