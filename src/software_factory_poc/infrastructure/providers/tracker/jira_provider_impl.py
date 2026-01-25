from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential

from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import TaskTrackerGatewayPort
from software_factory_poc.application.core.ports.gateways.dtos import TaskDTO
from software_factory_poc.application.core.domain.configuration.task_status import TaskStatus
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.tracker.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.application.core.domain.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.application.core.domain.configuration.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.infrastructure.providers.tracker.dtos.jira_status_enum import JiraStatus
import re
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_adf_builder import JiraAdfBuilder

logger = LoggerFactoryService.build_logger(__name__)


# Mapping from Domain Status to Infrastructure (Jira) Status
STATUS_MAPPING = {
    TaskStatus.TO_DO: JiraStatus.TO_DO,
    TaskStatus.IN_PROGRESS: JiraStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW: JiraStatus.IN_REVIEW,
    TaskStatus.DONE: JiraStatus.DONE,
}


class JiraProviderImpl(TaskTrackerGatewayPort):
    def __init__(self, http_client: JiraHttpClient):
        self.client = http_client
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
            payload = self._build_comment_payload(body)
            self._logger.debug(f"Sending comment payload to Jira: {payload}")
            
            response = self.client.post(f"rest/api/3/issue/{issue_key}/comment", payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
             self._handle_error(e, f"add_comment({issue_key})")
             raise

    def _build_comment_payload(self, body: Any) -> dict[str, Any]:
        """
        Constructs the Jira ADF payload.
        Handles both raw dicts (pass-through) and strings (smart formatting for emojis).
        """
        if isinstance(body, dict):
             return {"body": body}

        # If it's not a dict, treat as string and format
        text_body = str(body)
        payload_body = None
        
        # Case 1: Success
        if text_body.startswith("✅"):
            match = re.search(r"MR: (.+)", text_body)
            mr_link = match.group(1).strip() if match else "#"
            payload_body = JiraAdfBuilder.build_success_panel(
                title="Tarea Completada",
                summary="El scaffolding ha sido generado correctamente.",
                links={"🔗 Ver Merge Request": mr_link}
            )

        # Case 2: Failure
        elif text_body.startswith("❌"):
            try:
                parts = text_body.split(":", 1)
                summary = parts[0].replace("❌ ", "").strip()
                detail = parts[1].strip() if len(parts) > 1 else "Unknown error"
            except Exception:
                summary = "Fallo en generación"
                detail = text_body
                
            payload_body = JiraAdfBuilder.build_error_panel(
                error_summary="La ejecución se detuvo debido a un error.",
                technical_detail=f"{summary}\n{detail}"
            )

        # Case 3: Info / Branch Exists
        elif text_body.startswith("ℹ️ BRANCH_EXISTS|"):
            try:
                parts = text_body.split("|")
                branch_name = parts[1]
                branch_url = parts[2]

                payload_body = JiraAdfBuilder.build_info_panel(
                    title="Rama Existente Detectada",
                    details=f"La rama '{branch_name}' ya existe en el repositorio. "
                            f"Se asume que el trabajo fue generado previamente. "
                            f"La tarea pasará a revisión.",
                    links={"🔗 Ver Rama Existente": branch_url}
                )
            except IndexError:
                payload_body = JiraAdfBuilder.build_info_panel(
                    title="Rama Existente Detectada",
                    details=f"La rama existe, pero no se pudo parsear la URL. Mensaje original: {text_body}"
                )

        # Fallback: Standard Text
        if not payload_body:
            payload_body = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text_body}]
                    }
                ]
            }
        
        return {"body": payload_body}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        self._logger.info(f"Transitioning issue: {issue_key} to state matching: {transition_id}")
        try:
            # Note: The argument is named 'transition_id' to match the interface, 
            # but the implementation supports searching by name/keyword as per original requirements.
            target_status_keyword = transition_id
            
            # 1. Get available transitions
            response = self.client.get(f"rest/api/3/issue/{issue_key}/transitions")
            try:
                response.raise_for_status()
            except Exception as e:
                self._logger.error(f"Failed to fetch transitions for {issue_key}: {e}")
                raise e
                
            transitions = response.json().get("transitions", [])
            
            available_names = [t["name"] for t in transitions]
            self._logger.debug(f"Transitions available for {issue_key}: {available_names}")
    
            # 2. Find target ID with enhanced logic
            final_id = None
            keyword_lower = target_status_keyword.lower()
            
            # Strategy A: Exact Match (Case Insensitive)
            for t in transitions:
                if t["name"].lower() == keyword_lower:
                    final_id = t["id"]
                    self._logger.info(f"Transition '{transition_id}' found (Exact Match ID: {final_id})")
                    break
            
            # Strategy B: Partial Match (if no exact found)
            if not final_id:
                for t in transitions:
                    if keyword_lower in t["name"].lower() or keyword_lower in t["to"]["name"].lower():
                        final_id = t["id"]
                        self._logger.info(f"Transition '{transition_id}' found (Partial Match ID: {final_id})")
                        break
            
            if not final_id:
                error_msg = f"Transition '{transition_id}' not found. Available: {available_names}"
                self._logger.error(error_msg)
                raise ProviderError(
                    provider=TaskTrackerType.JIRA,
                    message=error_msg,
                    retryable=True
                )
    
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

    def transition_status(self, task_id: str, status: TaskStatus) -> None:
        """Adapts TaskTrackerGatewayPort.transition_status to internal transition_issue logic."""
        # Translate Domain Status to Infrastructure Status (String)
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
