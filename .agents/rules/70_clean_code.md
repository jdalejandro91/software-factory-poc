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

## 4) Tipos y Errores
- Tipado estricto en TODAS las firmas usando genéricos nativos de Python 3.12 (`list[str]`, `dict[str, Any]`). Prohibido `Any` salvo mapeos JSON inevitables de MCP.
- Errores tipados. **Prohibido** capturar `Exception` genérica y ocultar causa. Envolver errores I/O externos en excepciones de Dominio (`ProviderError`, `InfraError`) preservando stack/cause (`raise InfraError from e`).

## 5) Red flags (Rechazo Automático para Claude)
- Clases "God object".
- Lógica de negocio metida dentro de `infrastructure/`.
- Dependencias directas a detalles desde alto nivel (ej. importar `litellm` en `core/application/`).
- Comentarios que explican código confuso en lugar de refactorizar.