import base64
from typing import Any, Dict, Union, Optional

import httpx

from software_factory_poc.config.settings_pydantic import Settings, JiraAuthMode
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class JiraClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.jira_base_url.rstrip("/")
        self._validate_config()

    def _validate_config(self):
        self.settings.validate_jira_credentials()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        mode = self.settings.jira_auth_mode
        
        if mode == JiraAuthMode.CLOUD_API_TOKEN:
            email = self.settings.jira_user_email
            token = self.settings.jira_api_token.get_secret_value() if self.settings.jira_api_token else ""
            creds = f"{email}:{token}"
            encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"

        elif mode == JiraAuthMode.BASIC:
             email = self.settings.jira_user_email or ""
             token = self.settings.jira_api_token.get_secret_value() if self.settings.jira_api_token else ""
             creds = f"{email}:{token}"
             encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
             headers["Authorization"] = f"Basic {encoded}"

        elif mode == JiraAuthMode.BEARER:
            token = self.settings.jira_bearer_token.get_secret_value() if self.settings.jira_bearer_token else ""
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        logger.info(f"Fetching Jira issue: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers(), timeout=10.0)
            response.raise_for_status()
            return response.json()

    def add_comment(self, issue_key: str, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Agrega un comentario. Soporta ADF nativo (Dict) o texto simple (str).
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        logger.info(f"Adding comment to Jira issue: {issue_key}")

        payload = {}
        
        if isinstance(content, dict):
            payload = {"body": content}
        else:
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": str(content)}]
                        }
                    ]
                }
            }
        
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()

    def transition_issue(self, issue_key: str, target_status_keyword: str) -> bool:
        """
        Busca una transición disponible que contenga la palabra clave (ej: 'Review') y mueve el ticket.
        """
        # 1. Obtener transiciones disponibles para el estado actual
        url_get = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        
        with httpx.Client() as client:
            resp = client.get(url_get, headers=self._get_headers())
            resp.raise_for_status()
            transitions = resp.json().get("transitions", [])

        # 2. Buscar el ID de la transición deseada
        target_id = None
        target_name = ""
        
        # Normalizamos a minúsculas para búsqueda flexible
        keyword_lower = target_status_keyword.lower()
        
        for t in transitions:
            t_name = t["name"].lower()
            t_to = t["to"]["name"].lower()
            
            # Buscamos si el nombre de la transición O el estado destino coinciden
            if keyword_lower in t_name or keyword_lower in t_to:
                target_id = t["id"]
                target_name = t["name"]
                break
        
        if not target_id:
            logger.warning(f"No transition found containing '{target_status_keyword}' for issue {issue_key}. Available: {[t['name'] for t in transitions]}")
            return False

        # 3. Ejecutar la transición
        url_post = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        payload = {
            "transition": {
                "id": target_id
            }
        }
        
        logger.info(f"Transitioning issue {issue_key} to '{target_name}' (ID: {target_id})")
        
        with httpx.Client() as client:
            resp = client.post(url_post, headers=self._get_headers(), json=payload)
            resp.raise_for_status()
            return True