"""Evidence mapper: associate claims with evidence artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from epistemic_hygiene.claim_classifier import EpistemicClaim


def map_evidence(claims: List[EpistemicClaim], repo: Path) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for claim in claims:
        hits: List[str] = []
        for p in repo.rglob("*"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            if claim.text.strip() and claim.text.strip() in text:
                hits.append(str(p))
        mapping[claim.text] = hits
    return mapping
