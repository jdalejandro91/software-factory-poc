import logging
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode
from software_factory_poc.domain.value_objects.branch_name import BranchName
from software_factory_poc.domain.value_objects.file_content import FileContent
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent
from software_factory_poc.application.dtos.agent_request_dto import AgentRequestDTO
from software_factory_poc.application.contracts.llm_schemas import ScaffoldingResponseSchema

from software_factory_poc.application.ports.drivers.vcs_driver_port import VcsDriverPort
from software_factory_poc.application.ports.drivers.tracker_driver_port import TrackerDriverPort
from software_factory_poc.application.ports.drivers.research_driver_port import ResearchDriverPort
from software_factory_poc.application.ports.drivers.llm_driver_port import LlmDriverPort

logger = logging.getLogger(__name__)


class ScaffolderAgent:
    def __init__(self, vcs: VcsDriverPort, tracker: TrackerDriverPort, research: ResearchDriverPort,
                 llm: LlmDriverPort):
        self.vcs = vcs
        self.tracker = tracker
        self.research = research
        self.llm = llm

    async def execute(self, request: AgentRequestDTO) -> dict:
        if request.mode == ExecutionMode.DETERMINISTIC:
            logger.info(f"Modo DETERMINISTA: Iniciando Scaffolding para {request.ticket_id}")

            # 1. Recuperar contexto de herramientas REST (Cero LLM tokens)
            task_desc = await self.tracker.get_task_description(request.ticket_id)
            arch_context = await self.research.get_architecture_context(request.project_context_id)

            # 2. Inferencia Single-Shot (Forzamos la salida al Pydantic Schema)
            prompt = f"""
            Eres el Arquitecto Scaffolder. Genera el código para el requerimiento:
            [JIRA]: {task_desc}
            [CONFLUENCE]: {arch_context}
            """
            llm_dto: ScaffoldingResponseSchema = await self.llm.generate_structured(prompt, ScaffoldingResponseSchema)

            # 3. Mapeo a Agregados de Dominio (Aplica validaciones estrictas y guardrails)
            domain_files = [FileContent(f.path, f.content, f.is_new) for f in llm_dto.files]
            commit_intent = CommitIntent(
                branch=BranchName(llm_dto.branch_name),
                message=llm_dto.commit_message,
                files=domain_files
            )

            # 4. Driver MCP de VCS (Ejecuta el commit procedimentalmente sin LLM)
            commit_hash = await self.vcs.commit_changes(commit_intent)

            # 5. Cierra el ciclo en el Tracker
            await self.tracker.update_status(request.ticket_id, "IN_PROGRESS")
            await self.tracker.add_comment(
                request.ticket_id,
                f"✅ Scaffolding generado exitosamente. Commit Hash: {commit_hash}"
            )

            return {"status": "success", "hash": commit_hash}

        elif request.mode == ExecutionMode.AGENTIC:
            logger.info(f"Modo AGÉNTICO: Delegando control a LLM para {request.ticket_id}")
            # Solo pasamos las tools de MCP (VCS por ahora)
            available_tools = await self.vcs.get_mcp_tools()

            prompt = f"Eres BrahMAS Scaffolder. Investiga el ticket {request.ticket_id} y crea el scaffolding."
            result = await self.llm.run_agentic_loop(prompt, available_tools, self._tool_router)
            return {"status": "success", "result": result}

    async def _tool_router(self, tool_name: str, args: dict):
        """Enrutador Proxy para aislar herramientas MCP del LLM"""
        if tool_name.startswith("vcs_"):
            return await self.vcs.execute_tool(tool_name, args)
        raise ValueError(f"Herramienta no autorizada: {tool_name}")