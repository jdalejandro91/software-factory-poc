from typing import Any

from software_factory_poc.infrastructure.providers.tracker.mappers.jira_adf_primitives import (
    JiraAdfPrimitives,
)


class JiraAdfBuilder:
    """
    Builder for Atlassian Document Format (ADF) structures for Jira Cloud comments.
    Delegates primitive creation to JiraAdfPrimitives.
    """

    @classmethod
    def build_info_panel(cls, title: str, details: str, links: dict[str, str] = None) -> dict[str, Any]:
        panel_content = []
        
        # 1. Heading
        panel_content.append(JiraAdfPrimitives.create_heading(3, title))
        
        # 2. Details
        panel_content.append(JiraAdfPrimitives.create_paragraph([
            JiraAdfPrimitives.create_text(details)
        ]))

        # 3. Links List
        if links:
            panel_content.append(JiraAdfPrimitives.create_link_list(links))

        root_content = [
            JiraAdfPrimitives.create_panel("info", panel_content)
        ]
        return JiraAdfPrimitives.create_doc(root_content)

    @classmethod
    def build_error_panel(cls, error_summary: str, technical_detail: str) -> dict[str, Any]:
        panel_content = []
        
        # 1. Heading
        panel_content.append(JiraAdfPrimitives.create_heading(3, "No se pudo completar la Tarea"))
        
        # 2. Summary
        panel_content.append(JiraAdfPrimitives.create_paragraph([
            JiraAdfPrimitives.create_text(error_summary)
        ]))

        # 3. Technical Detail Label
        panel_content.append(JiraAdfPrimitives.create_paragraph([
            JiraAdfPrimitives.create_text("Detalle del Error:", marks=[{"type": "strong"}])
        ]))

        # 4. Technical Detail Code Block
        panel_content.append(JiraAdfPrimitives.create_code_block(str(technical_detail)))

        root_content = [
            JiraAdfPrimitives.create_panel("error", panel_content)
        ]
        return JiraAdfPrimitives.create_doc(root_content)

    @classmethod
    def build_success_panel(cls, title: str, summary: str, links: dict[str, str]) -> dict[str, Any]:
        panel_content = []
        
        # 1. Heading
        panel_content.append(JiraAdfPrimitives.create_heading(3, title))
        
        # 2. Summary
        panel_content.append(JiraAdfPrimitives.create_paragraph([
            JiraAdfPrimitives.create_text(summary)
        ]))

        # 3. Links List
        if links:
            panel_content.append(JiraAdfPrimitives.create_link_list(links))

        root_content = [
            JiraAdfPrimitives.create_panel("success", panel_content)
        ]
        
        return JiraAdfPrimitives.create_doc(root_content)
