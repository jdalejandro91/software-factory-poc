from dataclasses import dataclass
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode

@dataclass
class AgentRequestDTO:
    ticket_id: str
    project_context_id: str
    mode: ExecutionMode = ExecutionMode.DETERMINISTIC