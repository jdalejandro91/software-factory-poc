from software_factory_poc.application.core.interfaces.knowledge_base import KnowledgeBasePort

class ConfluenceMockAdapter(KnowledgeBasePort):
    def get_architecture_guidelines(self, url: str) -> str:
        if "carrito-de-compra" in url:
            return """0) Fuentes base: Clean Architecture (Robert C. Martin), Domain-Driven Design (Eric Evans).

1. Objetivo:
El sistema debe implementar un backend para un e-commerce, específicamente el módulo de Carrito de Compra (Shopping Cart). Debe ser agnóstico del framework (FastAPI por defecto) y desacoplar las reglas de negocio de la infraestructura.

2. Estructura de Proyecto (Hexagonal / Clean):
- src/
  - application/  (Casos de uso, puertos de entrada)
  - domain/       (Entidades, value objects, puertos de salida)
  - infrastructure/ (Adaptadores: DB, API, logs)
- tests/

3. Reglas:
- Las entidades no deben tener dependencias de frameworks.
- Los casos de uso orquestan el flujo.
- La infraestructura implementa las interfaces definidas en dominio.

4. Diagramas Requeridos:
- C4 mínimo (Context + Container)."""
        
        return "Guías de arquitectura estándar."
