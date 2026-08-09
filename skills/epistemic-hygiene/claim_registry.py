"""Claim registry: collect and track epistemic claims."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus


class ClaimRegistry:
    def __init__(self) -> None:
        self.claims: List[EpistemicClaim] = []

    def add(self, claim: EpistemicClaim) -> None:
        self.claims.append(claim)

    def to_json(self, path: Path) -> None:
        payload = [
            {
                "text": c.text,
                "source": c.source,
                "status": c.status.value,
                "confidence": c.confidence,
                "evidence": c.evidence or [],
                "operationalization": c.operationalization or "",
            }
            for c in self.claims
        ]
        path.write_text(json.dumps(payload, indent=2))

    def category_errors(self) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        for c in self.claims:
            if c.status == EpistemicStatus.METAPHOR and "fact" in c.text.lower():
                errors.append({"claim": c.text, "source": c.source, "error": "metaphor treated as fact"})
            if c.status == EpistemicStatus.UNKNOWN and c.confidence > 0.8:
                errors.append({"claim": c.text, "source": c.source, "error": "unknown claim with high confidence"})
        return errors
