import re
from typing import Any, Dict

from software_factory_poc.infrastructure.providers.tracker.mappers.jira_adf_builder import JiraAdfBuilder


class JiraPanelFactory:
    """
    Factory to create Jira ADF payloads based on text content rules.
    Decouples payload construction from the Provider implementation.
    """

    @staticmethod
    def create_payload(body: Any) -> Dict[str, Any]:
        """
        Constructs the Jira ADF payload.
        Handles both raw dicts (pass-through) and strings (smart formatting for emojis).
        """
        if isinstance(body, dict):
             # Enhanced mapping logic for Dict payloads
             msg_type = body.get("type", "")
             
             if msg_type == "scaffolding_success":
                 return {"body": JiraAdfBuilder.build_success_panel(
                     title=body.get("title", "Success"),
                     summary=body.get("summary", ""),
                     links=body.get("links", {})
                 )}

             if msg_type == "code_review_completion":
                 return {"body": JiraAdfBuilder.build_info_panel(
                     title=body.get("title", "Review Complete"),
                     details=body.get("summary", ""),
                     links=body.get("links", {})
                 )}
                 
             # Fallback: Safe conversion to standard paragraph
             return JiraPanelFactory._create_standard_payload(str(body))

        text_body = str(body)
        
        # Rule 1: Success (Legacy String)
        if text_body.startswith("✅"):
            return JiraPanelFactory._create_success_payload(text_body)

        # Rule 2: Failure
        if text_body.startswith("❌"):
            return JiraPanelFactory._create_failure_payload(text_body)

        # Rule 3: Info / Branch Exists
        from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages
        if text_body.startswith(ReporterMessages.BRANCH_EXISTS_PREFIX):
            return JiraPanelFactory._create_branch_exists_payload(text_body)

        # Fallback: Standard Text
        return JiraPanelFactory._create_standard_payload(text_body)

    @staticmethod
    def _create_success_payload(text_body: str) -> Dict[str, Any]:
        match = re.search(r"MR: (.+)", text_body)
        mr_link = match.group(1).strip() if match else "#"
        
        payload_body = JiraAdfBuilder.build_success_panel(
            title="Tarea Completada",
            summary="El scaffolding ha sido generado correctamente.",
            links={"🔗 Ver Merge Request": mr_link}
        )
        return {"body": payload_body}

    @staticmethod
    def _create_failure_payload(text_body: str) -> Dict[str, Any]:
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
        return {"body": payload_body}

    @staticmethod
    def _create_branch_exists_payload(text_body: str) -> Dict[str, Any]:
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
        return {"body": payload_body}

    @staticmethod
    def _create_standard_payload(text_body: str) -> Dict[str, Any]:
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
