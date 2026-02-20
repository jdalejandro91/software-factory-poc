# 20_clean_code.md — SPEC: Best Practices + Clean Code (Enforcement)

## 1) Principios Rectores
1. Correctness > Clarity > Simplicity > Performance.
2. Legibilidad primero. El código es para humanos.
3. DRY: Duplicación de conocimiento es deuda. Cada pieza de conocimiento tiene una única representación autoritativa.

## 2) SOLID (Obligatorio)
- **SRP:** Cada clase/método tiene UNA razón dominante para cambiar.
- **OCP:** Preferir extensión por polimorfismo/composicion sobre múltiples `if/switch`. (Ej. Implementar nuevos providers creando una nueva clase MCP Client, no modificando la capa Application).
- **DIP:** Alto nivel depende de abstracciones (`core/application/ports`). Detalles implementan abstracciones inyectadas vía DI.

## 3) Naming y Diseño de Métodos
- **Python PEP 8:** `snake_case` (funciones/variables), `PascalCase` (clases), `UPPER_CASE` (constantes).
- Nombres revelan intención. **Prohibido** nombres genéricos en la raíz (`utils.py`, `helpers.py`, `manager.py`).
- **Composed Method:** Métodos pequeños, granulares y "story-like". Hacer UNA cosa. Preferir early returns (guard clauses) en lugar de anidamiento profundo.

### **3.1. Regla de las 10 Líneas + Límite de Clase + Modularización Arquitectónica (MANDATORIO)**

- NINGÚN método funcional puede exceder **10 líneas de código lógico** (sin contar docstrings, firmas, imports o declaraciones de tipos).
- NINGUNA clase puede exceder **100 líneas de código lógico** (sin contar docstrings, firmas, imports o declaraciones de tipos).
- Si una clase supera el límite o muestra señales de mezclar responsabilidades (SRP), DEBES **subdividirla**.

#### **3.1.1. Regla de Subdivisión Controlada (cuando se divide una clase)**

Cuando subdividas una clase en varias:

- Debes **preservar estrictamente la arquitectura** y **todas** las pautas definidas en:

  * `.agents/CONSTITUTION.md`
  * `.agents/rules/**`
  * `.agents/skills/**`
- La subdivisión **NO** puede:

  * mover responsabilidades a capas incorrectas,
  * introducir dependencias cruzadas entre capas,
  * aumentar acoplamiento con infraestructura,
  * romper los contratos públicos existentes.
- Prioriza refactors por **extracción semántica**:

  * extrae **policies**, **adapters**, **mappers**, **validators**, **formatters**, **builders**, **strategies** o **workflows steps** (nombres explícitos y coherentes con el dominio).
- Si aparece lógica común, aplica **composición** y **interfaces estrechas** (ISP), evitando “helpers” genéricos.

#### **3.1.2. Regla de Archivo Único (legibilidad por estructura)**

- **Máximo 1 clase por archivo**.
- **Máximo 1 enumeración (Enum) por archivo**.
- Excepciones SOLO si es **estrictamente necesario por cohesión**, por ejemplo:

  * una clase privada interna muy pequeña que no tiene sentido fuera del archivo,
  * un Enum íntimamente ligado al tipo (y que romperlo empeoraría la legibilidad),
  * código generado (no tocar).
- Si aplicas una excepción, debes:

  * justificarla en 1–2 líneas en un comentario local tipo `# RATIONALE:` y
  * asegurar que no viola SRP ni incrementa acoplamiento.

#### **3.1.3. Regla de Impacto Cero (contratos y comportamiento)**

- El comportamiento funcional NO DEBE ALTERARSE: solo cambia estructura, nombres, distribución de responsabilidades y legibilidad.
- Los nombres de archivos deben reflejar su responsabilidad (evita `utils`, `helpers`, `common` ambiguos).
- No introduzcas nuevas dependencias externas ni frameworks “por limpieza”.

#### **3.1.4. Workflows: refactor obligatorio de `run/execute`**

- Revisa rigurosamente `run`/`execute` en:

  * `scaffolding_deterministic_workflow.py`
  * `code_review_deterministic_workflow.py`
- Deben quedar como **orquestadores** de pasos privados semánticos (sin lógica de negocio densa) sólo a través de la invocación de workflows.
- Prohibido anidamiento profundo: máximo 2 niveles de indentación por método.

## 4) Tipos y Errores
- Tipado estricto en TODAS las firmas usando genéricos nativos de Python 3.12 (`list[str]`, `dict[str, Any]`). Prohibido `Any` salvo mapeos JSON inevitables de MCP.
- Errores tipados. **Prohibido** capturar `Exception` genérica y ocultar causa. Envolver errores I/O externos en excepciones de Dominio (`ProviderError`, `InfraError`) preservando stack/cause (`raise InfraError from e`).

## 5) Red flags (Rechazo Automático para Claude)
- Clases "God object".
- Lógica de negocio metida dentro de `infrastructure/`.
- Dependencias directas a detalles desde alto nivel (ej. importar `litellm` en `core/application/`).
- Comentarios que explican código confuso en lugar de refactorizar.