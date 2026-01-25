import os
import shutil
from pathlib import Path

# Configuración de Rutas Base
BASE_DIR = Path("src/software_factory_poc/application/core/domain")
CONF_DIR = BASE_DIR / "configuration"
VO_DIR = BASE_DIR / "value_objects"
AGENTS_DIR = BASE_DIR / "agents"

# Definición de Movimientos: "Archivo": "Destino relativo dentro de agents/"
MOVES = {
    # --- COMMON ---
    "task_status.py": "common/config",
    "llm_provider_type.py": "common/config",
    "model_id.py": "common/value_objects",
    "trace_context.py": "common/value_objects",
    
    # --- VCS AGENT ---
    "vcs_provider_type.py": "vcs/config",
    
    # --- REPORTER AGENT ---
    "task_tracker_type.py": "reporter/config",
    
    # --- KNOWLEDGE AGENT ---
    "knowledge_provider_type.py": "knowledge/config",
    
    # --- REASONER AGENT ---
    "generation_config.py": "reasoner/value_objects",
    "message.py": "reasoner/value_objects",
    "message_role.py": "reasoner/value_objects",
    "output_constraints.py": "reasoner/value_objects",
    "output_format.py": "reasoner/value_objects",
    "prompt.py": "reasoner/value_objects",
    "structured_output_schema.py": "reasoner/value_objects",
    
    # --- SCAFFOLDING AGENT ---
    "scaffolding_agent_config.py": "scaffolding/config",
    "scaffolding_order.py": "scaffolding/value_objects"
}

def safe_move(filename, source_dir, dest_rel_path):
    """Mueve un archivo solo si existe en el origen."""
    src = source_dir / filename
    dest_dir = AGENTS_DIR / dest_rel_path
    dest = dest_dir / filename
    
    # Crear directorio destino si no existe
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    if src.exists():
        print(f"[MOVER] {filename} -> {dest_dir}")
        shutil.move(str(src), str(dest))
    elif dest.exists():
        print(f"[OK] {filename} ya estaba en el destino.")
    else:
        # Check inside subdirectories (e.g. if file is actually in value_objects but we checked configuration)
        # This is handled by main loop iterating both source dirs per definition
        pass

def update_scaffolding_config():
    """Reescribe el config solo si ya está en su lugar final."""
    target = AGENTS_DIR / "scaffolding/config/scaffolding_agent_config.py"
    if not target.exists():
        print("[WARN] ScaffoldingAgentConfig no encontrado en destino. Saltando actualización.")
        return

    print("[UPDATE] Actualizando ScaffoldingAgentConfig con nuevos campos...")
    content = """from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
# Imports relativos asumidos, se corregirán en el paso de refactor de imports
from ...common.value_objects.model_id import ModelId
from ...common.config.llm_provider_type import LlmProviderType
from ...vcs.config.vcs_provider_type import VcsProviderType
from ...reporter.config.task_tracker_type import TaskTrackerType
from ...knowledge.config.knowledge_provider_type import KnowledgeProviderType

@dataclass
class ScaffoldingAgentConfig:
    # Providers
    vcs_provider: VcsProviderType = field(default=VcsProviderType.GITLAB)
    tracker_provider: TaskTrackerType = field(default=TaskTrackerType.JIRA)
    knowledge_provider: KnowledgeProviderType = field(default=KnowledgeProviderType.CONFLUENCE)
    
    # LLM Settings
    llm_model_priority: List[ModelId] = field(default_factory=list)
    
    # Security & Paths
    project_allowlist: List[str] = field(default_factory=list)
    enable_secure_mode: bool = True
    work_dir: Path = Path("/tmp/scaffolding_workspace")
    architecture_page_id: str = ""
    
    # Legacy/Optional (Mantenidos por compatibilidad)
    model_name: str = "gpt-4"
    temperature: float = 0.0
"""
    target.write_text(content)

def main():
    print("--- INICIANDO MIGRACIÓN IDEMPOTENTE ---")
    
    # 1. Ejecutar movimientos desde Configuration
    print("\\nProcesando CONFIGURATION...")
    for f, d in MOVES.items():
        safe_move(f, CONF_DIR, d)

    # 2. Ejecutar movimientos desde Value Objects
    print("\\nProcesando VALUE OBJECTS...")
    for f, d in MOVES.items():
        # Intentamos mover desde VO si no estaba en Conf (algunos archivos pueden estar en uno u otro)
        safe_move(f, VO_DIR, d)

    # 3. Actualizar código
    update_scaffolding_config()

    # 4. Limpieza (Solo si están vacíos)
    print("\\nLimpiando directorios antiguos...")
    try:
        if CONF_DIR.exists() and not any(CONF_DIR.iterdir()):
            CONF_DIR.rmdir()
            print("Directorio configuration eliminado.")
        if VO_DIR.exists() and not any(VO_DIR.iterdir()):
            VO_DIR.rmdir()
            print("Directorio value_objects eliminado.")
    except Exception as e:
        print(f"Nota: No se pudieron eliminar carpetas antiguas (posiblemente no vacías): {e}")

    print("\\n--- MIGRACIÓN COMPLETADA ---")

if __name__ == "__main__":
    main()
