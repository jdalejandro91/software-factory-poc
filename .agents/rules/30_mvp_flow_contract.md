# 30_mvp_flow_contract.md — El Protocolo de Ejecución (12 Steps)

Objetivo: Definir estrictamente qué entra y qué sale de cada paso del flujo principal. Cero magia, cero suposiciones.

## 1. El Objeto Maestro: `ScaffoldingOrder`
Este es el objeto de dominio (Value Object) que nace en el Entrypoint y viaja hasta el `ScaffoldingAgent`.

```python
class ScaffoldingOrder(BaseModel):
    issue_key: str          # "PROJ-123"
    project_id: str         # "group/repo" o ID numérico
    feature_description: str # "Crear un CRUD de usuarios..."
    branch_name: str        # "feature/proj-123-crud-usuarios"
    base_branch: str        # "develop"
2. El Flujo de los 12 Pasos (Step-by-Step Contract)
El ScaffoldingAgent.execute_flow es el director. Abajo se define el contrato de sus sub-llamadas.

Step 1: Trigger & Mapping (Infrastructure Layer)
Actor: JiraTriggerRouter -> CreateScaffoldingUseCase

Input: JSON sucio del Webhook de Jira.

Output: ScaffoldingOrder (Limpio y validado).

Regla: Si el JSON no tiene los campos mínimos, retorna 400 Bad Request y no despierta al Agente.

Step 2: Report Start
Actor: ReporterAgent.report_start

Input: issue_key

Output: void (Side Effect: Comentario en Jira "🤖 Iniciando Scaffolding...").

Step 3: Idempotency Check (Branch Validation)
Actor: VcsAgent.validate_branch_existence

Input: project_id, branch_name

Output: bool (exists).

Control Flow:

Si True: El Agente reporta "Rama ya existe" y TERMINA la ejecución (Success state).

Si False: Continúa al paso 4.

Step 4: Research Context
Actor: ResearchAgent.research_task

Input: feature_description + project_id

Output: ResearchResult (String markdown con contexto técnico, documentación relevante, snippets, etc.).

Step 5: Prompt Assembly
Actor: ScaffoldingPromptBuilder.build (Tool pura)

Input: ScaffoldingOrder + ResearchResult

Output: Prompt (Objeto con system_message, user_message y constraints).

Step 6: Reasoning (LLM Generation)
Actor: ReasonerAgent.generate_code

Input: Prompt + model_preference (config)

Output: LlmResponse (String crudo con el texto generado por el modelo).

Regla: El Reasoner delega al LlmGateway la selección del proveedor (OpenAI/DeepSeek/Gemini).

Step 7: Artifact Parsing
Actor: ArtifactParser.parse (Tool pura)

Input: LlmResponse.content (String)

Output: List[FileContentDTO]

Contrato de FileContentDTO:

Python
path: str    # "src/users/user_service.py"
content: str # "class UserService..."
language: str # "python"
Fallo: Si el parser falla (formato inválido), se lanza ContractParseError.

Step 8: Create Branch
Actor: VcsAgent.create_branch

Input: project_id, branch_name, base_branch

Output: void (Lanza ProviderError si falla).

Step 9: Commit Files
Actor: VcsAgent.commit_files

Input: project_id, branch_name, List[FileContentDTO], commit_message

Output: commit_hash (str).

Step 10: Create Merge Request
Actor: VcsAgent.create_merge_request

Input: project_id, source_branch, target_branch, title, description

Output: mr_url (str).

Step 11: Report Success
Actor: ReporterAgent.report_success

Input: issue_key, mr_url

Output: void (Side Effect: Comentario en Jira "✅ Éxito: Ver MR").

Step 12: Transition Task
Actor: ReporterAgent.transition_task

Input: issue_key, target_status (ej. "IN REVIEW")

Output: void.

3. Manejo de Fallos (Failure Contracts)
Si algo explota en medio del flujo, el ScaffoldingAgent debe capturarlo y ejecutar una limpieza elegante.

Scenario A: Error de Infraestructura (Jira caído, GitLab timeout)
Excepción: ProviderError (capturada en execute_flow).

Acción:

Log error con traceback.

Llamar a ReporterAgent.report_failure(issue_key, error_summary).

NO reintentar infinitamente (el reintento es responsabilidad del Provider con @retry, no del Agente).

Scenario B: Error de Parsing (LLM alucinó el formato)
Excepción: ContractParseError.

Acción:

Reportar fallo en Jira: "El modelo generó código inválido".

(Futuro) Podría activar un "Self-Correction Loop", pero en MVP falla hard.

Scenario C: Error de Seguridad (Allowlist)
Excepción: SecurityViolationError (ej. intento de sobrescribir .gitlab-ci.yml).

Acción:

Bloquear commit.

Reportar incidente.

4. Estructuras de Datos Críticas (DTOs)
Python
# Lo que el Parser le entrega al VCS
class FileContentDTO(BaseModel):
    path: str
    content: str

# Lo que el LLM le devuelve al Agente
class LlmResponse(BaseModel):
    content: str
    token_usage: dict
    model_used: str