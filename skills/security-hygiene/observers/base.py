"""Security observers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class ObservationRecord:
    observer_id: str
    expected: str
    actual: str
    match: bool
    details: dict[str, Any] = field(default_factory=dict)
    evidence_ref: str = field(default_factory=lambda: f"obs_{datetime.now().isoformat()}")


class Observer(ABC):
    observer_id: str = ""

    @abstractmethod
    def observe(self, target: dict[str, Any]) -> ObservationRecord:
        raise NotImplementedError
