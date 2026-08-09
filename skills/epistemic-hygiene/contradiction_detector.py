"""Contradiction detector: find conflicting claims."""
from __future__ import annotations

from typing import List, Tuple

from epistemic_hygiene.claim_classifier import EpistemicClaim


def detect_contradictions(claims: List[EpistemicClaim]) -> List[Tuple[EpistemicClaim, EpistemicClaim]]:
    pairs: List[Tuple[EpistemicClaim, EpistemicClaim]] = []
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            if _conflicts(a.text, b.text):
                pairs.append((a, b))
    return pairs


def _conflicts(a: str, b: str) -> bool:
    if not a or not b:
        return False
    al = a.lower()
    bl = b.lower()
    return ("always" in al and "never" in bl) or ("never" in al and "always" in bl)
