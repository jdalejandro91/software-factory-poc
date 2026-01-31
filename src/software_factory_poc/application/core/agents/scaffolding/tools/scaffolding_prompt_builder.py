from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import ScaffoldingOrder
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ScaffoldingPromptBuilder:
    """
    Tool responsible for constructing the prompt for the Reasoner Agent.
    Heavily optimized to respect Technology Stack and RAG Context structures.
    """

    def build_prompt(self, request: ScaffoldingOrder, knowledge_context: str) -> str:
        knowledge_context = self._validate_context(knowledge_context, request.issue_key)

        system_section = self._get_role_definition(request)
        context_section = self._format_rag_context(knowledge_context)
        task_section = self._format_task_instructions(request)
        example_section = self._get_example_output()

        full_prompt = f"{system_section}\n{context_section}\n{task_section}\n{example_section}"
        logger.info(f"--- [DEBUG] PROMPT GENERATED FOR STACK: {request.technology_stack} ---")
        logger.info(f"⬇️ --- FULL PROMPT START --- ⬇️\n{full_prompt}\n⬆️ --- FULL PROMPT END --- ⬆️")

        return full_prompt

    def _validate_context(self, context: str, issue_key: str) -> str:
        if not context or not context.strip():
            return "No specific documentation provided. Follow standard best practices."
        return context

    def _get_role_definition(self, request: ScaffoldingOrder) -> str:
        return (
            f"ROLE: You are a Principal Software Architect specializing in **{request.technology_stack}**.\n"
            f"MISSION: Generate the exact file structure and configuration for the project '{request.issue_key}'."
        )

    def _format_rag_context(self, context: str) -> str:
        return (
            f"================================================================\n"
            f"SOURCE OF TRUTH (CONFLUENCE ARCHITECTURE DOC)\n"
            f"================================================================\n"
            f"The text below defines the MANDATORY architecture (e.g. Modular Monolith, Hexagonal).\n"
            f"You MUST extract the folder structure defined here:\n\n"
            f"{context}\n"
            f"================================================================\n"
        )

    def _format_task_instructions(self, request: ScaffoldingOrder) -> str:
        return (
            f"--- TASK SPECIFICATION ---\n"
            f"1. **TECHNOLOGY STACK**: {request.technology_stack}\n"
            f"   - You MUST use file extensions, config files, and conventions matching this stack.\n"
            f"   - Example: If NestJS, use 'nest-cli.json', '.ts' files, 'app.module.ts'.\n"
            f"   - Example: If Python/FastAPI, use 'pyproject.toml', 'main.py'.\n\n"

            f"2. **BUSINESS GOAL**: {request.summary}\n"
            f"   - Extract business modules (e.g., 'cart', 'payment') from the goal or the Confluence doc.\n\n"

            f"3. **OUTPUT RULES (STRICT)**:\n"
            f"   - **Structure**: If the Confluence doc explicitly lists folders like 'src/modules/catalog', YOU MUST CREATE THEM.\n"
            f"   - **Files**: Generate VALID, production-ready content for root config (Dockerfile, package.json/.gitlab-ci.yml).\n"
            f"   - **Placeholders**: For logic files inside modules, provide a README.md explaining what goes there, OR a skeleton class/interface. Do NOT leave them missing.\n"
            f"   - **Format**: Return ONLY a JSON list.\n"
        )

    def _get_example_output(self) -> str:
        # FIX: Usamos doble llave {{ }} para escapar y que Python imprima una llave literal en el string final.
        return (
            f"--- JSON OUTPUT EXAMPLE (Adapt structure to Confluence doc) ---\n"
            f"[\n"
            f"  {{\"path\": \".gitignore\", \"content\": \"node_modules/\\ndist/\"}},\n"
            f"  {{\"path\": \"nest-cli.json\", \"content\": \"{{...}}\"}},\n"
            f"  {{\"path\": \"src/main.ts\", \"content\": \"import {{ NestFactory }} ...\"}},\n"
            f"  {{\"path\": \"src/modules/cart/cart.module.ts\", \"content\": \"@Module({{...}}) export class CartModule {{}}\"}},\n"
            f"  {{\"path\": \"src/modules/cart/domain/README.md\", \"content\": \"Domain entities for Cart go here.\"}}\n"
            f"]\n"
        )