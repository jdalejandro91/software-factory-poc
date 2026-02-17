# 10_clean_architecture.md — SPEC: Clean Architecture Pragmática

## 0) Objetivo
Mantener un sistema multi-agente robusto donde la lógica pura y las integraciones ("Tools") estén completamente desacopladas. Prioridad: reemplazabilidad de proveedores, coexistencia tecnológica, trazabilidad y seguridad.

## 1) Modelo de Capas y Reglas de Dependencia
Las dependencias solo apuntan hacia adentro:
- **Domain:** Tipos del negocio. CERO dependencias a I/O, SDKs (`mcp`, `litellm`), HTTP, FS.
- **Application:** Define cómo se logra el trabajo (Agents & Skills). Expone `ports/` (interfaces abstractas).
- **Infrastructure:** Implementa `ports/` usando `mcp` y `litellm`. I/O real. Solo transporte y adaptación. **NO decisiones del flujo** ("si falla el MR entonces reintenta" NO va en el adapter, va en Application). Errores envueltos en `ProviderError`.

## 2) El Anti-patrón de "Usecaseitis"
- NO convertir cada microacción en un "UseCase" separado (ej. `CreateBranchUseCase`).
- En su lugar, el flujo se controla mediante **Skills** ejecutables (ej. `ChangeSkill`) que agrupan lógicamente interacciones con múltiples **Ports**.

## 3) Falsa Agencialidad
- **Falsa Agencialidad:** `vcs`, `tracker`, `research` NO SON AGENTES. Son Ports/Tools que consumen herramientas externas.
- **Agentes Reales:** Un `Agent` por flujo (ej: `ScaffolderAgent`). Decide orden, construye comandos, y evalúa policies.