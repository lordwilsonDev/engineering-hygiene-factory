"""Epistemic Governor: enforcing transition rules with evidence requirements."""
from __future__ import annotations

import hashlib
import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
from epistemic_hygiene.status_updater import can_transition

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_id: str
    claim_id: str
    artifact_path: str
    content_hash: str
    created_at: str
    artifact_type: str  # 'test_result', 'state_diff', 'log', 'measurement'
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]


class TransitionRejection(Exception):
    def __init__(self, claim_id: str, from_status: str, to_status: str, reason: str):
        self.claim_id = claim_id
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        super().__init__(f"Rejected {claim_id}: {from_status} -> {to_status}: {reason}")


class EpistemicGovernor:
    """Enforces epistemic status transitions with evidence requirements."""

    def __init__(self, evidence_root: Path):
        self.evidence_root = Path(evidence_root)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self._claims: Dict[str, EpistemicClaim] = {}
        self._evidence: Dict[str, List[EvidenceArtifact]] = {}
        self._rejection_log: List[Dict[str, Any]] = []
        self._transition_log: List[Dict[str, Any]] = []

    def register_claim(self, claim: EpistemicClaim) -> None:
        self._claims[claim.text] = claim
        self._evidence.setdefault(claim.text, [])

    def add_evidence(self, claim: EpistemicClaim, artifact: EvidenceArtifact) -> None:
        if artifact.claim_id != claim.text:
            raise ValueError(f"Evidence artifact claim_id mismatch: {artifact.claim_id} != {claim.text}")
        self._evidence.setdefault(claim.text, []).append(artifact)

    def _validate_evidence(self, claim_id: str) -> List[EvidenceArtifact]:
        artifacts = self._evidence.get(claim_id, [])
        valid = []
        for art in artifacts:
            path = Path(art.artifact_path)
            if not path.exists():
                logger.warning("Evidence artifact missing: %s", path)
                continue
            content = path.read_bytes()
            if EvidenceArtifact.compute_hash(content) != art.content_hash:
                logger.warning("Evidence hash mismatch: %s", path)
                continue
            try:
                payload = json.loads(content.decode("utf-8"))
                if payload.get("claim_id") != claim_id:
                    logger.warning("Evidence claim_id mismatch inside artifact: %s", path)
                    continue
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("Evidence artifact not valid JSON: %s: %s", path, exc)
                continue
            valid.append(art)
        return valid

    def transition(self, claim: EpistemicClaim, to_status: EpistemicStatus, evidence_paths: Optional[List[Path]] = None) -> EpistemicClaim:
        from_status = claim.status
        claim_id = claim.text

        if not can_transition(from_status, to_status):
            reason = f"transition not allowed: {from_status.value} -> {to_status.value}"
            self._record_rejection(claim_id, from_status, to_status, reason)
            raise TransitionRejection(claim_id, from_status.value, to_status.value, reason)

        if from_status == EpistemicStatus.ASSERTED and to_status in {
            EpistemicStatus.TESTED, EpistemicStatus.SUPPORTED, EpistemicStatus.VALIDATED
        }:
            valid_evidence = self._validate_evidence(claim_id)
            if not valid_evidence:
                reason = "insufficient evidence"
                self._record_rejection(claim_id, from_status, to_status, reason)
                raise TransitionRejection(claim_id, from_status.value, to_status.value, reason)

        if to_status == EpistemicStatus.VALIDATED:
            current = self._claims.get(claim_id, claim)
            if current.status != EpistemicStatus.TESTED:
                reason = "VALIDATED requires claim to be in TESTED status first"
                self._record_rejection(claim_id, from_status, to_status, reason)
                raise TransitionRejection(claim_id, from_status.value, to_status.value, reason)
            valid_evidence = self._validate_evidence(claim_id)
            independent_artifacts = {a.artifact_id for a in valid_evidence}
            if len(independent_artifacts) < 2:
                reason = "VALIDATED requires at least 2 independent evidence artifacts"
                self._record_rejection(claim_id, from_status, to_status, reason)
                raise TransitionRejection(claim_id, from_status.value, to_status.value, reason)

        updated = EpistemicClaim(
            text=claim.text,
            source=claim.source,
            status=to_status,
            confidence=claim.confidence,
            evidence=[e.artifact_path for e in self._validate_evidence(claim_id)],
            operationalization=claim.operationalization,
        )
        self._claims[claim_id] = updated
        self._transition_log.append({
            "claim_id": claim_id,
            "from": from_status.value,
            "to": to_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(self._validate_evidence(claim_id)),
        })
        return updated

    def _record_rejection(self, claim_id, from_status, to_status, reason):
        entry = {
            "claim_id": claim_id,
            "from": from_status.value if hasattr(from_status, 'value') else str(from_status),
            "to": to_status.value if hasattr(to_status, 'value') else str(to_status),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._rejection_log.append(entry)

    def get_claim(self, claim_id: str) -> EpistemicClaim:
        return self._claims.get(claim_id)

    def get_rejection_log(self) -> List[Dict]:
        return list(self._rejection_log)

    def get_transition_log(self) -> List[Dict]:
        return list(self._transition_log)


class RestorationVerifier:
    """Independent state-diff verifier that does NOT trust the restoration routine."""

    def __init__(self, scope_paths: List[Path]):
        self.scope_paths = [Path(p).resolve() for p in scope_paths]

    def capture_state(self) -> Dict[str, Any]:
        snapshot = {}
        for base in self.scope_paths:
            if not base.exists():
                continue
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    try:
                        snapshot[str(p)] = {
                            "size": p.stat().st_size,
                            "mtime": p.stat().st_mtime,
                        }
                    except OSError:
                        snapshot[str(p)] = {"size": -1, "mtime": -1}
        return snapshot

    def diff(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        added = {k: v for k, v in after.items() if k not in before}
        removed = {k: v for k, v in before.items() if k not in after}
        modified = {k: (before[k], v) for k, v in after.items() if k in before and before[k] != v}
        return {
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "added": added,
            "removed": removed,
            "modified": modified,
            "restoration_verified": len(added) == 0 and len(removed) == 0 and len(modified) == 0,
        }
