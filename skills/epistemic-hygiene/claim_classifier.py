"""Epistemic claim classifier."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class EpistemicStatus(str, Enum):
    ASSERTED = "asserted"
    OBSERVED = "observed"
    TESTED = "tested"
    SUPPORTED = "supported"
    VALIDATED = "validated"
    FALSIFIED = "falsified"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EpistemicClaim:
    text: str
    source: str
    status: EpistemicStatus
    confidence: float
    evidence: Optional[List[str]] = None
    operationalization: Optional[str] = None
