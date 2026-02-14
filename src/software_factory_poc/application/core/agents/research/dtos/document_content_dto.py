from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class DocumentContentDTO:
    """
    Represents the content of a single documentation page or file.
    """
    title: str
    url: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
