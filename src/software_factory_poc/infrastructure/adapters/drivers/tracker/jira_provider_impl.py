from typing import Any
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.application.ports.drivers.common.config.task_status import TaskStatus
from software_factory_poc.application.ports.drivers.common.exceptions import (
    ProviderError,
)
from software_factory_poc.application.ports.drivers.reporter.config.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.ports.drivers.reporter.ports.task_tracker_gateway import TaskTrackerGateway
from software_factory_poc.application.core.domain.entities.task import Task, TaskDescription
from software_factory_poc.infrastructure.configuration.jira_settings import JiraSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.adapters.drivers.tracker.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.infrastructure.adapters.drivers.tracker.dtos.jira_status_enum import JiraStatus
from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_description_mapper import JiraDescriptionMapper

logger = LoggerFactoryService.build_logger(__name__)

# Mapping from Domain Status to Infrastructure (Jira) Status
STATUS_MAPPING = {
    TaskStatus.TO_DO: JiraStatus.TO_DO,
    TaskStatus.IN_PROGRESS: JiraStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW: JiraStatus.IN_REVIEW,
    TaskStatus.DONE: JiraStatus.DONE,
}


class JiraProviderImpl(TaskTrackerGateway):
    def __init__(self, http_client: JiraHttpClient, settings: JiraSettings):
        self.client = http_client
        self.settings = settings
        self._logger = logger
        self.mapper = JiraDescriptionMapper()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_task(self, issue_key: str) -> Task:
        """Retrieves a Domain Task entity."""
        self._logger.info(f"Fetching Task Entity: {issue_key}")
        try:
            json_data = self.get_issue(issue_key)
            fields = json_data.get("fields", {})

            # Map Description using ADF Mapper
            adf_desc = fields.get("description")
            domain_desc = self.mapper.to_domain(adf_desc)

            return Task(
                id=json_data.get("id", "0"),
                key=json_data.get("key"),
                project_key=fields.get("project", {}).get("key", "UNKNOWN"),
                issue_type=fields.get("issuetype", {}).get("name", "Task"),
                summary=fields.get("summary", ""),
                status=fields.get("status", {}).get("name", "Unknown"),
                description=domain_desc
            )
        except Exception as e:
            self._handle_error(e, f"get_task({issue_key})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_issue(self, issue_key: str) -> dict[str, Any]:
        self._logger.info(f"Fetching Jira issue JSON: {issue_key}")
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
            from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_panel_factory import \
                JiraPanelFactory
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
            retryable=False
        )

    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Adapts TaskTrackerGatewayPort.transition_status to internal transition_issue logic."""
        if status == TaskStatus.IN_REVIEW:
            transition_name = self.settings.transition_in_review
            self._logger.info(f"Transitioning {task_id} to IN_REVIEW using configured transition: '{transition_name}'")
            self.transition_issue(task_id, transition_name)
            return

        jira_target_status = STATUS_MAPPING.get(status)

        if jira_target_status:
            self.transition_issue(task_id, jira_target_status.value)
        else:
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
    def update_task_description(self, task_id: str, description: TaskDescription) -> None:
        """
        Updates the task description in Jira.
        1. Cleans old code blocks from the raw text.
        2. Uses Mapper to generate the structured ADF payload.
        3. Sends the payload to Jira.
        """
        self._logger.info(f"Updating description for task: {task_id}")
        
        try:
            # 1. Defensive Cleaning: Remove any existing code blocks from the human text
            # This prevents duplication if the mapper extraction wasn't perfect previously
            clean_raw_content = description.raw_content
            
            # Regex to strip Jira {code}...{code} blocks
            clean_raw_content = re.sub(r'\{code(?:[:|][^\}]*)?\}.*?\{code\}', '', clean_raw_content, flags=re.DOTALL | re.IGNORECASE)
            # Regex to strip Markdown ```...``` blocks
            clean_raw_content = re.sub(r'```.*?```', '', clean_raw_content, flags=re.DOTALL)
            
            clean_raw_content = clean_raw_content.strip()

            # 2. Create a clean DTO
            clean_description = TaskDescription(
                raw_content=clean_raw_content,
                config=description.config
            )

            # 3. Map to ADF (Atlassian Document Format)
            # The mapper handles creating the "codeBlock" node.
            adf_payload = self.mapper.to_adf(clean_description)
            
            self._logger.info("✅ Generated ADF payload with native codeBlock.")

            # 4. Send Request
            payload = {
                "fields": {
                    "description": adf_payload
                }
            }
            response = self.client.put(f"rest/api/3/issue/{task_id}", payload)
            response.raise_for_status()
            
        except Exception as e:
            self._handle_error(e, f"update_task_description({task_id})")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def append_issue_description(self, task_id: str, content: str) -> None:
        self._logger.info(f"Appending content to task: {task_id}")
        try:
            issue = self.get_issue(task_id)
            current_desc = issue.get("fields", {}).get("description")

            new_paragraph = {
                "type": "paragraph",
                "content": [{"type": "text", "text": "\n" + content}]
            }

            if not current_desc:
                updated_desc = {
                    "type": "doc",
                    "version": 1,
                    "content": [new_paragraph]
                }
            elif current_desc.get("type") == "doc" and isinstance(current_desc.get("content"), list):
                current_desc["content"].append(new_paragraph)
                updated_desc = current_desc
            else:
                self._logger.warning(f"Unknown description format for {task_id}. Resetting to valid ADF.")
                updated_desc = {
                    "type": "doc",
                    "version": 1,
                    "content": [new_paragraph]
                }

            payload = {"fields": {"description": updated_desc}}
            response = self.client.put(f"rest/api/3/issue/{task_id}", payload)
            response.raise_for_status()

        except Exception as e:
            self._handle_error(e, f"append_issue_description({task_id})")
            raise