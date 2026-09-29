"""
Entidad de Dominio Company: Modela una organizacion o escuela en la plataforma.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Company:
    id: str
    name: str
    fiscal_id: Optional[str] = None
    tax_config: Dict[str, Any] = field(default_factory=dict)
    worklog_definitions: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @property
    def is_personal(self) -> bool:
        return self.name.lower() == "personal"
