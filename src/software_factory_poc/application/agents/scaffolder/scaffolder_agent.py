import logging
import re
from datetime import datetime, timezone

from software_factory_poc.application.agents.common.base_agent import BaseAgent
# Ports (Interfaces) — Unica dependencia permitida desde el Dominio
from software_factory_poc.application.drivers.vcs.vcs_driver import VcsDriver
from software_factory_poc.application.drivers.tracker.tracker_driver import TrackerDriver
from software_factory_poc.application.drivers.research.research_driver import ResearchDriver
from software_factory_poc.application.drivers.brain.brain_driver import BrainDriver

# Domain Entities & Value Objects
from software_factory_poc.domain.entities.task import Task
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent
from software_factory_poc.domain.value_objects.vcs.branch_name import BranchName
from software_factory_poc.domain.value_objects.vcs.file_content import FileContent

# Application Contracts & Tools
from software_factory_poc.application.agents.scaffolder.contracts.scaffolder_contracts import ScaffoldingResponseSchema
from software_factory_poc.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import ScaffoldingPromptBuilder

logger = logging.getLogger(__name__)


class ScaffolderAgent(BaseAgent):
    """
    Agente Scaffolder BrahMAS — Modo Determinista.

    Orquesta la creacion de codigo base (scaffolder) siguiendo un flujo
    rigido de 6 fases / 12 pasos, consumiendo exclusivamente Puertos inyectados.

    Flujo:
      1. Report Start    → tracker.add_comment
      2. Validation       → vcs.validate_branch_existence
      3. Context          → research.get_architecture_context
      4. Reasoning        → prompt_builder + llm.generate_structured
      5. Action           → vcs.create_branch + vcs.commit_changes + vcs.create_merge_request
      6. Final Report     → tracker.add_comment (metadata + success) + tracker.update_status
    """

    def __init__(
        self,
        vcs: VcsDriver,
        tracker: TrackerDriver,
        research: ResearchDriver,
        brain: BrainDriver,
        prompt_builder: ScaffoldingPromptBuilder,
    ):
        super().__init__(name="ScaffolderAgent", role="Orchestrator", goal="Orchestrate scaffolder creation", brain=brain)
        self.vcs = vcs
        self.tracker = tracker
        self.research = research
        self.prompt_builder = prompt_builder

    # ══════════════════════════════════════════════════════════════
    #  Flujo Principal (Determinista)
    # ══════════════════════════════════════════════════════════════

    async def execute_flow(self, task: Task) -> None:
        """Ejecuta el flujo completo de scaffolder para una tarea de dominio."""
        logger.info(f"[Scaffolder] Iniciando flujo para tarea {task.key}")

        try:
            # ── PASO 1: Report Start ──
            await self.tracker.add_comment(
                task.key,
                "Iniciando tarea de Scaffolding (BrahMAS Engine)...",
            )

            # ── Extraccion de configuracion del Task ──
            config = task.description.config
            service_name = config.get("parameters", {}).get("service_name", "")
            gitlab_project_id = (
                config.get("target", {}).get("gitlab_project_id", "")
                or config.get("target", {}).get("gitlab_project_path", "")
            )
            target_branch = config.get("target", {}).get("default_branch", "main")

            branch_name = self._build_branch_name(task.key, service_name)

            # ── PASO 2: Validation — Idempotency Check ──
            branch_exists = await self.vcs.validate_branch_existence(branch_name)

            if branch_exists:
                msg = (
                    f"La rama '{branch_name}' ya existe en el repositorio. "
                    "Deteniendo ejecucion para evitar sobreescritura."
                )
                logger.warning(f"[Scaffolder] {msg}")
                await self.tracker.add_comment(task.key, msg)
                await self.tracker.update_status(task.key, "In Review")
                return

            # ── PASO 3: Context — Investigacion Arquitectonica ──
            logger.info("[Scaffolder] Investigando contexto arquitectonico...")
            arch_context = await self.research.get_architecture_context(
                service_name or task.key,
            )

            # ── PASO 4: Reasoning — Prompt + LLM ──
            logger.info("[Scaffolder] Construyendo prompt y generando codigo...")
            prompt = self.prompt_builder.build_prompt_from_task(task, arch_context)

            scaffold_plan: ScaffoldingResponseSchema = await self.brain.generate_structured(
                prompt=prompt,
                schema_cls=ScaffoldingResponseSchema,
            )

            if not scaffold_plan.files:
                raise ValueError("El LLM genero 0 archivos. No se puede continuar.")

            # ── PASO 5a: Action — Crear rama ──
            logger.info(f"[Scaffolder] Creando rama '{branch_name}'...")
            await self.vcs.create_branch(branch_name, ref=target_branch)

            # ── PASO 5b: Action — Commit de archivos ──
            logger.info(f"[Scaffolder] Commiteando {len(scaffold_plan.files)} archivos...")
            intent = self._build_commit_intent(branch_name, scaffold_plan)
            commit_hash = await self.vcs.commit_changes(intent)

            # ── PASO 5c: Action — Crear Merge Request ──
            logger.info("[Scaffolder] Creando Merge Request...")
            mr_url = await self.vcs.create_merge_request(
                source_branch=branch_name,
                target_branch=target_branch,
                title=f"feat: Scaffolding {task.key}",
                description=f"Auto-generated by BrahMAS.\n\n{task.summary}",
            )

            # ── PASO 6a: Final Report — Metadata YAML ──
            metadata_comment = self._build_metadata_comment(
                gitlab_project_id=gitlab_project_id,
                branch_name=branch_name,
                mr_url=mr_url,
            )
            await self.tracker.add_comment(task.key, metadata_comment)

            # ── PASO 6b: Final Report — Comentario de exito ──
            success_msg = (
                f"Scaffolding completado exitosamente.\n"
                f"- Merge Request: {mr_url}\n"
                f"- Rama: {branch_name}\n"
                f"- Commit: {commit_hash}\n"
                f"- Archivos generados: {len(scaffold_plan.files)}"
            )
            await self.tracker.add_comment(task.key, success_msg)

            # ── PASO 6c: Final Report — Transicion a IN REVIEW ──
            await self.tracker.update_status(task.key, "In Review")

            logger.info(f"[Scaffolder] Tarea {task.key} completada exitosamente. MR: {mr_url}")

        except Exception as e:
            logger.error(f"[Scaffolder] Error critico en tarea {task.key}: {e}", exc_info=True)
            await self._report_failure(task.key, e)
            raise

    # ══════════════════════════════════════════════════════════════
    #  Metodos privados auxiliares
    # ══════════════════════════════════════════════════════════════

    def _build_branch_name(self, task_key: str, service_name: str = "") -> str:
        """Construye un nombre de rama deterministico y seguro a partir del task key."""
        safe_key = re.sub(r"[^a-z0-9\-]", "", task_key.lower())
        if service_name:
            safe_service = re.sub(r"[^a-z0-9\-]", "-", service_name.lower().strip())
            return f"feature/{safe_key}-{safe_service}"
        return f"feature/{safe_key}-scaffolder"

    def _build_commit_intent(
        self, branch_name: str, scaffold_plan: ScaffoldingResponseSchema
    ) -> CommitIntent:
        """Convierte la respuesta del LLM en un CommitIntent de dominio."""
        domain_files = [
            FileContent(path=f.path, content=f.content, is_new=f.is_new)
            for f in scaffold_plan.files
        ]

        return CommitIntent(
            branch=BranchName(value=branch_name),
            message=scaffold_plan.commit_message,
            files=domain_files,
        )

    def _build_metadata_comment(
        self, gitlab_project_id: str, branch_name: str, mr_url: str
    ) -> str:
        """Construye el bloque YAML de metadata para inyectar en la tarea de Jira."""
        generated_at = datetime.now(timezone.utc).isoformat()
        return (
            "BrahMAS Automation Metadata:\n"
            "```yaml\n"
            "code_review_params:\n"
            f"  gitlab_project_id: \"{gitlab_project_id}\"\n"
            f"  source_branch_name: \"{branch_name}\"\n"
            f"  review_request_url: \"{mr_url}\"\n"
            f"  generated_at: \"{generated_at}\"\n"
            "```"
        )

    async def _report_failure(self, task_key: str, error: Exception) -> None:
        """Reporta el fallo a Jira antes de relanzar la excepcion."""
        try:
            await self.tracker.add_comment(
                task_key,
                f"Fallo en Scaffolding: {error}",
            )
        except Exception as report_err:
            logger.error(
                f"[Scaffolder] No se pudo reportar el fallo a Jira: {report_err}",
            )
