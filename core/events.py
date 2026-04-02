from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class GameEvent:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
