from dataclasses import dataclass
from typing import Optional
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode

@dataclass
class AgentRequestDTO:
    ticket_id: str
    project_context_id: str
    mode: ExecutionMode = ExecutionMode.DETERMINISTIC
    merge_request_id: Optional[str] = None