from dataclasses import dataclass

@dataclass
class ReporterMessages:
    START_SCAFFOLDING = "🤖 Iniciando tarea de scaffolding..."
    SUCCESS_PREFIX = "✅ Éxito: "
    FAILURE_PREFIX = "❌ Fallo: "
