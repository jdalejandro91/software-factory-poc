# 50_safety_and_dod.md — Security, Policies, Idempotency, and DoD

## 1. Seguridad y Redacción (Regla de Hierro)
- NUNCA hardcodear tokens. Consumirlos desde `infrastructure/configuration/`. NUNCA commitear `.env`.
- Todo log interactuando con el exterior DEBE pasar por la lógica de redacción (`RedactionService`) para ocultar tokens/credenciales.
- No loggear Prompts o Respuestas de LLM crudas de forma completa si contienen datos sensibles; usar extractos sanitizados.

## 2. El Rol de las Policies (`core/application/policies/`)
- La aplicación DEBE consultar las políticas antes de invocar un Puerto que mutará el estado externo.
- **Ejemplos de Policy:** No permitir auto-merge a `main`, validar allowlists de repositorios, o bloquear nombres de ramas inválidos. Las políticas deben ser clases puras, sin I/O.

## 3. Idempotencia y Estado (`core/domain/run/`)
Toda ejecución de una Mission genera un `Run`. 
- Cada paso de una Skill genera un `RunStep` con una clave de idempotencia (`idempotency_key = hash(run_id + task_ref + step_name)`).
- Antes de ejecutar I/O real (ej. abrir un MR), la aplicación consulta el `RunStorePort` en `infrastructure/persistence/run_store/`. Si el paso ya ocurrió con éxito, se retorna el artefacto guardado sin duplicar la petición al exterior.

## 4. Definition of Done (Criterios de Aceptación para Claude)
Un feature o refactor está "DONE" solo si:
1. **Zero Zombie Code:** Se eliminaron de la rama de trabajo las clases de REST manual, clientes HTTP custom, ADF Builders, y Gateways de LLM obsoletos.
2. **Architecture Check:** `uv run ruff check .` y `uv run mypy src/` pasan con 0 errores. La regla de dependencia hacia `core/` se respeta al 100%.
3. **Dual Flow Soportado:** Se diferencia claramente la lógica entre `skills/` (determinista) y `agents/` (agéntico) en la orquestación.
4. **Coexistencia Aislada:** La infraestructura enruta las peticiones de los Ports dinámicamente al cliente MCP correspondiente basándose en el contexto del VO, ocultando la lógica a Application.