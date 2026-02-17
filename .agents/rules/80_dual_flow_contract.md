# 30_dual_flow_contract.md — The Dual Flow (Autonomía Progresiva)

Cada Agente (`core/application/agents/`) debe soportar y gobernar dos modos de ejecución. Ambos enfoques utilizan **MCP** en la infraestructura para la interacción con el mundo exterior. Nunca usar APIs REST manuales.

## Modo A: LINEAR_DETERMINISTIC (Flujo Lineal Determinista)
**Para tareas de baja/media complejidad, altamente predecibles y de optimización de costos.**
1. **Definición:** El Agente orquesta clases en `core/application/skills/` secuencialmente (ej. `FetchDiffSkill` -> `AnalyzeCodeSkill` -> `PublishCommentSkill`).
2. **Ejecución MCP:** Las `Skills` son código Python puro que invocan los métodos de los `Ports` explícitamente. La infraestructura traduce estas llamadas a invocaciones de herramientas MCP.
3. **Invocación LLM Mínima:** El LLM se llama de forma puntual (*One-Shot*) solo cuando se requiere análisis semántico o síntesis (ej. pedirle al `LlmPort` que transforme código y lo devuelva en un Pydantic Model). El LLM NUNCA controla el flujo de ejecución.

## Modo B: AGENTIC_ACT_LOOP (Bucle Agéntico ReAct)
**Para misiones complejas, exploratorias o resolución de problemas ambiguos (Diagnosis, Self-Healing).**
1. **Definición:** El Agente entra en un ciclo de razonamiento (`Think -> Act -> Observe`).
2. **Inyección de MCP:** El Agente recolecta los esquemas de las herramientas disponibles a través de sus `Ports`, las filtra por la capa `policies/` (para denegar operaciones destructivas), y se las expone al `LlmPort` (vía LiteLLM Tool Calling).
3. **Autonomía:** El LLM recibe la `Mission` y decide qué herramienta invocar. El bucle Python de la aplicación atrapa la intención, ejecuta el llamado de la herramienta en el Puerto, y devuelve el resultado al LLM en el siguiente ciclo hasta completar el objetivo.