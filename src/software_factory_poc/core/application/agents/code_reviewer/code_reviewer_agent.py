import logging
import re

# Application Contracts & Tools
from software_factory_poc.core.application.agents.code_reviewer.contracts.code_reviewer_contracts import (
    CodeReviewResponseSchema,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.common.agent_execution_mode import (
    AgentExecutionMode,
)
from software_factory_poc.core.application.agents.common.base_agent import AgentIdentity, BaseAgent
from software_factory_poc.core.application.ports.brain_port import BrainPort
from software_factory_poc.core.application.ports.docs_port import DocsPort
from software_factory_poc.core.application.ports.tracker_port import TrackerPort

# Ports (Interfaces)
from software_factory_poc.core.application.ports.vcs_port import VcsPort

# Domain Entities & Value Objects
from software_factory_poc.core.domain.mission.entities.mission import Mission
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.core.domain.quality.value_objects.review_comment import ReviewComment
from software_factory_poc.core.domain.quality.value_objects.review_severity import ReviewSeverity

logger = logging.getLogger(__name__)


class CodeReviewerAgent(BaseAgent):
    """
    Agente Code Reviewer BrahMAS — Modo Determinista.

    Audita Merge Requests existentes usando contexto enriquecido (Confluence)
    y publica el resultado en GitLab + Jira.

    Flujo:
      1. Pre-check   → Validar metadata (mr_url, gitlab_project_id)
      2. Fetch        → vcs.get_merge_request_diff + research.get_architecture_context
      3. Analyze      → prompt_builder + llm.generate_structured → CodeReviewReport
      4. Publish      → vcs.publish_review + tracker.post_review_summary + transicion condicional
    """

    def __init__(
        self,
        vcs: VcsPort,
        tracker: TrackerPort,
        research: DocsPort,
        brain: BrainPort,
        prompt_builder: CodeReviewPromptBuilder,
        execution_mode: AgentExecutionMode = AgentExecutionMode.DETERMINISTIC,
    ):
        super().__init__(
            identity=AgentIdentity(
                name="CodeReviewerAgent",
                role="Reviewer",
                goal="Perform automated code reviews",
            ),
            brain=brain,
            execution_mode=execution_mode,
        )
        self._vcs = vcs
        self._tracker = tracker
        self._research = research
        self._prompt_builder = prompt_builder

    # ══════════════════════════════════════════════════════════════
    #  Flujo Principal (Determinista)
    # ══════════════════════════════════════════════════════════════

    async def _run_deterministic(self, mission: Mission) -> None:
        """Implementa el contrato de BaseAgent delegando al flujo de code review."""
        return await self.execute_flow(mission)

    async def execute_flow(self, mission: Mission) -> None:
        """Ejecuta el flujo completo de code review para una tarea de dominio."""
        logger.info(f"[Reviewer] Iniciando revision para tarea {mission.key}")

        try:
            await self._tracker.add_comment(
                mission.key,
                "Iniciando analisis de codigo (BrahMAS Code Review)...",
            )

            # ── PASO 1: Pre-check — Validar metadata inyectada por el Scaffolder ──
            cr_params = mission.description.config.get("code_review_params", {})
            mr_url = cr_params.get("review_request_url", "")
            gitlab_project_id = cr_params.get("gitlab_project_id", "")

            if not mr_url:
                raise ValueError(
                    "No se encontro 'review_request_url' en la metadata de la tarea. "
                    "El Scaffolder debe inyectar estos datos antes del Code Review."
                )
            if not gitlab_project_id:
                raise ValueError("No se encontro 'gitlab_project_id' en la metadata de la tarea.")

            mr_iid = self._extract_mr_iid(mr_url)
            logger.info(f"[Reviewer] MR IID extraido: {mr_iid} | Project: {gitlab_project_id}")

            # ── PASO 2: Fetch — Obtener diff y contexto tecnico ──
            logger.info("[Reviewer] Descargando diff del MR...")
            mr_diff = await self._vcs.get_merge_request_diff(mr_iid)

            logger.info("[Reviewer] Consultando estandares de arquitectura...")
            conventions = await self._research.get_architecture_context(mission.summary)

            # ── PASO 3: Analyze — Construir prompt y razonar con LLM ──
            logger.info("[Reviewer] Analizando codigo con LLM...")
            sys_prompt = self._prompt_builder.build_system_prompt()
            user_prompt = self._prompt_builder.build_analysis_prompt(
                mission_summary=mission.summary,
                mission_desc=mission.description.raw_content,
                mr_diff=mr_diff,
                conventions=conventions,
            )

            # Combinar system + user prompt (el puerto solo acepta un prompt)
            full_prompt = f"{sys_prompt}\n\n{user_prompt}"

            review_schema: CodeReviewResponseSchema = await self._brain.generate_structured(
                prompt=full_prompt,
                schema=CodeReviewResponseSchema,
                priority_models=[],
            )

            # Convertir respuesta del LLM al agregado de dominio con invariantes
            report = self._to_domain_report(review_schema)

            # ── PASO 4a: Publish — Publicar review en GitLab (MR comments) ──
            logger.info("[Reviewer] Publicando comentarios en GitLab...")
            await self._vcs.publish_review(mr_iid, report)

            # ── PASO 4b: Publish — Publicar resumen ejecutivo en Jira ──
            logger.info("[Reviewer] Publicando resumen en Jira...")
            await self._tracker.post_review_summary(mission.key, report)

            # ── PASO 4c: Publish — Transicion condicional ──
            if report.is_approved:
                await self._tracker.add_comment(
                    mission.key,
                    f"Code Review APROBADO. El MR cumple los estandares de calidad.\nMR: {mr_url}",
                )
            else:
                await self._tracker.add_comment(
                    mission.key,
                    f"Code Review RECHAZADO. Se requieren cambios antes de aprobar.\n"
                    f"Issues encontrados: {len(report.comments)}\n"
                    f"MR: {mr_url}",
                )
                await self._tracker.update_status(mission.key, "Changes Requested")

            verdict = "APROBADO" if report.is_approved else "RECHAZADO"
            logger.info(f"[Reviewer] Tarea {mission.key} revisada. Veredicto: {verdict}")

        except Exception as e:
            logger.error(f"[Reviewer] Error critico en tarea {mission.key}: {e}", exc_info=True)
            await self._report_failure(mission.key, e)
            raise

    # ══════════════════════════════════════════════════════════════
    #  Metodos privados auxiliares
    # ══════════════════════════════════════════════════════════════

    def _extract_mr_iid(self, mr_url: str) -> str:
        """Extrae el MR IID de una URL de GitLab Merge Request."""
        match = re.search(r"merge_requests/(\d+)", mr_url)
        if match:
            return match.group(1)
        if mr_url.strip().isdigit():
            return mr_url.strip()
        raise ValueError(f"No se pudo extraer MR IID de la URL: '{mr_url}'")

    def _to_domain_report(self, schema: CodeReviewResponseSchema) -> CodeReviewReport:
        """Convierte la respuesta del LLM (Pydantic) al agregado de dominio CodeReviewReport."""
        domain_comments = [
            ReviewComment(
                file_path=issue.file_path,
                description=issue.description,
                suggestion=issue.suggestion,
                severity=ReviewSeverity(issue.severity),
                line_number=issue.line_number,
            )
            for issue in schema.issues
        ]

        has_critical = any(c.severity == ReviewSeverity.CRITICAL for c in domain_comments)
        is_approved = schema.is_approved and not has_critical

        return CodeReviewReport(
            is_approved=is_approved,
            summary=schema.summary,
            comments=domain_comments,
        )

    async def _report_failure(self, mission_key: str, error: Exception) -> None:
        """Reporta el fallo a Jira antes de relanzar la excepcion."""
        try:
            await self._tracker.add_comment(
                mission_key,
                f"Error ejecutando revision automatica: {error}",
            )
        except Exception as report_err:
            logger.error(
                f"[Reviewer] No se pudo reportar el fallo a Jira: {report_err}",
            )
