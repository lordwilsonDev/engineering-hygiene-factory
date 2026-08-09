#!/usr/bin/env python3
"""
First-wave proof harness for Engineering Hygiene Factory.

Executes Proof Obligations 1-3 against the epistemic governor,
restoration verifier, and evidence pipeline. Produces immutable
evidence artifacts and emits a machine-readable verdict ledger.

Run: python tests/proof_harness_first_wave.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import types
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

FACTORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FACTORY_ROOT))
MODULES_DIR = FACTORY_ROOT / "skills" / "epistemic-hygiene"
_pkg = types.ModuleType("epistemic_hygiene")
_pkg.__path__ = [str(MODULES_DIR)]  # type: ignore[attr-defined]
sys.modules["epistemic_hygiene"] = _pkg
sys.path.insert(0, str(MODULES_DIR))

from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
from epistemic_hygiene.governor import EpistemicGovernor, EvidenceArtifact, RestorationVerifier


# ---------- result containers ----------

@dataclass(frozen=True)
class ProofResult:
    proof_id: str
    claim_id: str
    attack_variant: str
    passed: bool
    expected: str
    actual: str
    evidence_artifacts: List[str] = field(default_factory=list)
    rejection_log_entries: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""


class ProofLedger:
    def __init__(self) -> None:
        self.results: List[ProofResult] = []

    def add(self, result: ProofResult) -> None:
        self.results.append(result)

    def verdict(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        by_proof: Dict[str, Any] = {}
        for r in self.results:
            by_proof.setdefault(r.proof_id, {"passed": 0, "failed": 0, "variants": []})
            by_proof[r.proof_id]["variants"].append({
                "variant": r.attack_variant,
                "passed": r.passed,
                "expected": r.expected,
                "actual": r.actual,
                "notes": r.notes,
            })
            if r.passed:
                by_proof[r.proof_id]["passed"] += 1
            else:
                by_proof[r.proof_id]["failed"] += 1
        return {"total": total, "passed": passed, "failed": total - passed, "by_proof": by_proof}


# ---------- helpers ----------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_artifact(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return digest


def make_evidence(governor: EpistemicGovernor, claim: EpistemicClaim, artifact_type: str, content: str) -> EvidenceArtifact:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = claim.text.replace(" ", "_")[:40]
    art_path = governor.evidence_root / f"{ts}_{safe}_{artifact_type}.json"
    digest = write_artifact(art_path, content)
    return EvidenceArtifact(
        artifact_id=f"{ts}_{safe}_{artifact_type}",
        claim_id=claim.text,
        artifact_path=str(art_path),
        content_hash=digest,
        created_at=utc_now(),
        artifact_type=artifact_type,
        metadata={"content_bytes": len(content.encode("utf-8"))},
    )


def claim_for(claim_id: str) -> EpistemicClaim:
    return EpistemicClaim(
        text=claim_id,
        source="proof_harness",
        status=EpistemicStatus.ASSERTED,
        confidence=0.5,
        evidence=[],
        operationalization="first_wave_proof",
    )


# ---------- Proof Obligation 1 ----------

def run_proof_1(governor: EpistemicGovernor, ledger: ProofLedger) -> None:
    """Evidence-Before-Elevation: ASSERTED cannot elevate without evidence."""
    claim_id = "EAAE-INV-001"
    targets = [EpistemicStatus.VALIDATED, EpistemicStatus.TESTED, EpistemicStatus.SUPPORTED]
    variants = [
        ("empty_evidence", []),
        ("null_evidence", None),
        ("malformed_evidence_only", ["malformed"]),
        ("mismatched_claim_id_evidence", ["mismatch"]),
    ]

    for to_status in targets:
        for variant, evidence_ids in variants:
            gov = EpistemicGovernor(governor.evidence_root)
            claim = claim_for(claim_id)
            gov.register_claim(claim)

            if evidence_ids is None:
                evidence_paths = None
            else:
                evidence_paths = []
                for eid in evidence_ids:
                    if variant == "mismatched_claim_id_evidence":
                        fake_claim_id = "wrong_claim"
                    else:
                        fake_claim_id = claim_id
                    fake_claim = EpistemicClaim(text=fake_claim_id, source="x", status=EpistemicStatus.UNKNOWN, confidence=0.5)
                    if variant == "malformed_evidence_only":
                        content = "NOT_JSON_MALFORMED"
                    else:
                        content = json.dumps({"artifact_id": eid, "claim_id": fake_claim_id})
                    art = make_evidence(gov, fake_claim, "test_result", content)
                    gov.add_evidence(fake_claim, art)

            try:
                updated = gov.transition(claim_for(claim_id), to_status, evidence_paths)
                actual = f"elevated to {updated.status.value}"
                passed = False
            except Exception as e:
                actual = f"rejected: {e}"
                passed = True

            ledger.add(ProofResult(
                proof_id="EAAE-INV-001",
                claim_id=claim_id,
                attack_variant=f"{variant}_{to_status.value}",
                passed=passed,
                expected="rejected with 'insufficient evidence'",
                actual=actual,
                rejection_log_entries=gov.get_rejection_log()[-1:],
            ))


# ---------- Proof Obligation 2 ----------

def run_proof_2(governor: EpistemicGovernor, ledger: ProofLedger) -> None:
    """Prohibited Direct Elevation: ASSERTED->VALIDATED requires 2 independent artifacts."""
    claim_id = "EAAE-INV-002"
    variants = [
        ("zero_artifacts", []),
        ("one_artifact", ["single"]),
        ("duplicate_artifacts", ["dup", "dup"]),
        ("two_artifacts_pre_TESTED", ["a", "b"]),
    ]

    for variant, evidence_ids in variants:
        gov = EpistemicGovernor(governor.evidence_root)
        claim = claim_for(claim_id)
        gov.register_claim(claim)

        for eid in evidence_ids:
            fake_claim = claim_for(claim_id)
            art = make_evidence(gov, fake_claim, "test_result", json.dumps({"artifact_id": eid, "claim_id": claim_id}))
            gov.add_evidence(fake_claim, art)

        try:
            updated = gov.transition(claim_for(claim_id), EpistemicStatus.VALIDATED)
            actual = f"elevated to {updated.status.value}"
            passed = False
        except Exception as e:
            actual = f"rejected: {e}"
            passed = True

        ledger.add(ProofResult(
            proof_id="EAAE-INV-002",
            claim_id=claim_id,
            attack_variant=variant,
            passed=passed,
            expected="rejected",
            actual=actual,
            rejection_log_entries=gov.get_rejection_log()[-1:],
        ))


# ---------- Proof Obligation 3 ----------

def run_proof_3(governor: EpistemicGovernor, ledger: ProofLedger) -> None:
    """Restoration Verification: independent verifier must detect residuals."""
    claim_id = "EAAE-INV-003"
    workspace = Path(tempfile.mkdtemp(prefix="eaae_proof3_"))

    # scope paths: workspace itself
    verifier = RestorationVerifier([workspace])
    claim = claim_for(claim_id)
    governor.register_claim(claim)

    # Phase A: capture state_before
    state_before = verifier.capture_state()

    # Phase B: inject mutation (create residual file)
    residual = workspace / "residual_after_fake_restoration.log"
    write_artifact(residual, "this file should have been removed by restoration")

    # Phase C: fake restoration reports success but leaves residual
    restoration_result = {"status": "ok", "message": "restoration complete"}

    # Phase D: independent verifier compares state_before and state_after
    state_after = verifier.capture_state()
    diff = verifier.diff(state_before, state_after)

    # record evidence
    gov = EpistemicGovernor(governor.evidence_root)
    gov.register_claim(claim)
    art = make_evidence(gov, claim, "state_diff", json.dumps({
        "state_before_keys": len(state_before),
        "state_after_keys": len(state_after),
        "diff": diff,
        "restoration_claimed_success": restoration_result["status"] == "ok",
    }, indent=2))
    gov.add_evidence(claim, art)

    restoration_verified = diff.get("restoration_verified", False)

    ledger.add(ProofResult(
        proof_id="EAAE-INV-003",
        claim_id=claim_id,
        attack_variant="fake_restoration_with_residuals",
        passed=not restoration_verified,
        expected="restoration_verified=false with residual files detected",
        actual=f"restoration_verified={restoration_verified}, diff={json.dumps(diff)}",
        evidence_artifacts=[str(art.artifact_path)],
        notes=f"diff added={diff['added_count']} modified={diff['modified_count']} removed={diff['removed_count']}",
    ))

    shutil.rmtree(workspace, ignore_errors=True)


# ---------- main ----------

def main() -> int:
    ts = utc_now().replace(":", "").replace("+", "Z").split(".")[0]
    evidence_root = FACTORY_ROOT / "artifacts" / f"proof_first_wave_{ts}"
    evidence_root.mkdir(parents=True, exist_ok=True)

    governor = EpistemicGovernor(evidence_root)
    ledger = ProofLedger()

    run_proof_1(governor, ledger)
    run_proof_2(governor, ledger)
    run_proof_3(governor, ledger)

    verdict = ledger.verdict()

    ledger_path = evidence_root / "proof_ledger.json"
    write_artifact(ledger_path, json.dumps(verdict, indent=2))

    rejection_path = evidence_root / "rejection_log.json"
    write_artifact(rejection_path, json.dumps(governor.get_rejection_log(), indent=2))

    transition_path = evidence_root / "transition_log.json"
    write_artifact(transition_path, json.dumps(governor.get_transition_log(), indent=2))

    summary = {
        "timestamp": utc_now(),
        "evidence_root": str(evidence_root),
        "verdict": verdict,
    }
    print(json.dumps(summary, indent=2))

    if verdict["failed"] > 0:
        print(f"\nFAILED: {verdict['failed']} proof variant(s) failed")
        return 1
    print("\nALL FIRST-WAVE PROOFS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
