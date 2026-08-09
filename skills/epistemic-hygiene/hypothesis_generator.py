"""Hypothesis generator: convert unknowns into testable hypotheses."""
from __future__ import annotations

from typing import List

from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus


def generate_hypotheses(claims: List[EpistemicClaim]) -> List[EpistemicClaim]:
    out: List[EpistemicClaim] = []
    for c in claims:
        if c.status == EpistemicStatus.UNKNOWN:
            out.append(
                EpistemicClaim(
                    text=f"FALSIFIABLE: {c.text}",
                    source=c.source,
                    status=EpistemicStatus.HYPOTHESIS,
                    confidence=0.5,
                    evidence=c.evidence,
                    operationalization="Define measurable quantities and baseline for comparison.",
                )
            )
    return out
