"""Base classes for security mutations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class MutationResult:
    success: bool
    observation: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    recovered: bool = False
    recovery_action: str | None = None
    logs: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat)


@dataclass
class RecoveryResult:
    success: bool
    state_restored: bool = False
    verification: bool = False
    logs: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MutationPlugin(ABC):
    mutation_id: str = ""
    risk_level: str = "medium"
    claim_ids: list[str] = field(default_factory=list)

    @abstractmethod
    def preconditions(self, target: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def apply(self, target: dict[str, Any]) -> MutationResult:
        raise NotImplementedError

    @abstractmethod
    def recovery_strategy(self, target: dict[str, Any], failure: Exception | None = None) -> RecoveryResult:
        raise NotImplementedError
