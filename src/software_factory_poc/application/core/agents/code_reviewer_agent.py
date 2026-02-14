import logging
from software_factory_poc.domain.entities.task import Task
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode
from software_factory_poc.domain.value_objects.review_severity import ReviewSeverity
from software_factory_poc.domain.value_objects.review_comment import ReviewComment
from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport
from software_factory_poc.application.contracts.llm_schemas import CodeReviewResponseSchema

from software_factory_poc.application.ports.drivers.vcs_driver_port import VcsDriverPort
from software_factory_poc.application.ports.drivers.tracker_driver_port import TrackerDriverPort
from software_factory_poc.application.ports.drivers.research_driver_port import ResearchDriverPort
from software_factory_poc.application.ports.drivers.llm_driver_port import LlmDriverPort
from software_factory_poc.application.core.agents.code_review_prompt_builder import CodeReviewPromptBuilder

logger = logging.getLogger(__name__)


class CodeReviewerAgent:
    def __init__(
            self, vcs: VcsDriverPort, tracker: TrackerDriverPort,
            research: ResearchDriverPort, llm: LlmDriverPort,
            mode: ExecutionMode, default_arch_page_id: str
    ):
        self.vcs = vcs
        self.tracker = tracker
        self.research = research
        self.llm = llm
        self.mode = mode
        self.default_arch_page_id = default_arch_page_id

    async def execute(self, task: Task) -> dict:
        """El Agente actúa como Application Service recibiendo la Entidad Task."""

        # Extracción de la configuración YAML ya parseada en la Entidad
        mr_iid = str(task.description.config.get("merge_request_iid", ""))
        arch_page_id = str(task.description.config.get("architecture_doc_page_id", self.default_arch_page_id))

        if not mr_iid or mr_iid == "None":
            raise ValueError(f"El ticket {task.key} no contiene 'merge_request_iid' en su YAML.")

        if self.mode == ExecutionMode.DETERMINISTIC:
            logger.info(f"Modo DETERMINISTA: Analizando MR {mr_iid} para {task.key}")

            # 1. Recuperar contexto procedural (0 Tokens LLM, sin llamar a Jira extra)
            conventions = await self.research.get_architecture_context(arch_page_id)
            mr_diff = await self.vcs.get_merge_request_diff(mr_iid)

            if not mr_diff.strip():
                return {"status": "success", "review_result": "Aprobado (Cero cambios de código)"}

            # 2. Inferencia Single-Shot (Fuerza la salida del Pydantic Schema)
            sys_prompt = CodeReviewPromptBuilder.build_system_prompt()
            analysis_prompt = CodeReviewPromptBuilder.build_analysis_prompt(
                task.summary, task.description.raw_content, mr_diff, conventions
            )

            llm_dto: CodeReviewResponseSchema = await self.llm.generate_structured(
                prompt=analysis_prompt, schema_cls=CodeReviewResponseSchema, system_prompt=sys_prompt
            )

            # 3. Mapeo a Agregado de Dominio (Ejecuta Guardrails de instanciación)
            domain_issues = []
            for i in llm_dto.issues:
                try:
                    domain_issues.append(
                        ReviewComment(i.file_path, i.description, i.suggestion, ReviewSeverity(i.severity),
                                      i.line_number))
                except ValueError as e:
                    logger.warning(f"Alucinación omitida: {e}")

            # Autocorrección del Agregado
            is_approved = llm_dto.is_approved
            if is_approved and any(i.severity == ReviewSeverity.CRITICAL for i in domain_issues):
                is_approved = False
                logger.warning("Auto-corrección: El LLM intentó aprobar con issues CRITICAL. Forzando RECHAZO.")

            report = CodeReviewReport(is_approved=is_approved, summary=llm_dto.summary, comments=domain_issues)

            # 4. Publicar Resultados vía MCP en GitLab y ADF en Jira
            await self.vcs.publish_review(mr_iid, report)
            await self.tracker.post_review_summary(task.key, report)

            return {"status": "success", "review_result": "Aprobado" if report.is_approved else "Rechazado"}

        elif self.mode == ExecutionMode.AGENTIC:
            available_tools = await self.vcs.get_mcp_tools() + await self.tracker.get_mcp_tools()
            result = await self.llm.run_agentic_loop(
                prompt=f"Audita el MR {mr_iid} del ticket {task.key}.",
                available_tools=available_tools, tool_executor=self._tool_router
            )
            return {"status": "success", "result": result}

    async def _tool_router(self, tool_name: str, args: dict):
        if tool_name.startswith("vcs_"): return await self.vcs.execute_tool(tool_name, args)
        if tool_name.startswith("tracker_"): return await self.tracker.execute_tool(tool_name, args)
        raise ValueError(f"Herramienta no autorizada: {tool_name}")