#!/usr/bin/env python3
"""Business-deliverable claim container contract (blueprint P2 producer).

sovereign-outcome-engine emits a machine-readable claim container next to
each report declaring what the deliverable CLAIMS (scan was read-only, score
is N, deal terms are X) with evidence refs. These tests enforce the contract
shape on the producer side so a deliverable can never claim more than its
evidence supports.

The producer-side contract is verified two ways:
  1. Static: outcome_engine.py must contain the emit_claim_container function
     and call it from main() (the wire exists, not just a definition).
  2. Behavioral: the factory's validate_claim_containers adapter accepts a
     well-formed container and rejects tampered ones (missing fields, invalid
     tier, missing evidence file). This is the ledger-side gate that would run
     against any emitted container.

The behavioral tests build containers in a tmp dir, so they are hermetic and
zero-spend; they never touch the real SOE artifacts tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_claim_containers import (  # noqa: E402
    validate_container,
    validate_dir,
)

SOE_ENGINE = Path.home() / "sovereign-outcome-engine" / "outcome_engine.py"
VALID_TIERS = {f"T{i}" for i in range(7)}


def _valid_container(repo_root: Path, report_name: str = "ferree_report.html") -> dict:
    (repo_root / report_name).write_text("<html>report</html>", encoding="utf-8")
    return {
        "deliverable_id": "soe:ferree:20260810T000000Z",
        "deliverable_type": "outcome_report",
        "produced_by": "sovereign-outcome-engine",
        "generated_at": "20260810T000000Z",
        "industry": "Logistics / Moving",
        "claims": [
            {
                "claim_id": "soe:ferree:scan_readonly",
                "subject": "Ferree data scan",
                "claim_type": "computed_result",
                "assertion": "Scanned 100 files read-only",
                "verification_tier": "T2",
                "verdict": "VERIFIED",
                "evidence": [{"path": report_name, "kind": "report_artifact"}],
                "evaluated_at": "20260810T000000Z",
            }
        ],
    }


def _write(container: dict, path: Path) -> None:
    path.write_text(json.dumps(container, indent=2), encoding="utf-8")


def test_valid_container_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "artifacts" / "business" / "claim_container_ferree.json"
    path.parent.mkdir(parents=True)
    _write(_valid_container(repo), path)
    report = validate_container(path, repo_root=repo)
    assert report["violation_count"] == 0, report


def test_missing_claim_field_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "claim_container_x.json"
    c = _valid_container(repo)
    del c["claims"][0]["verification_tier"]
    _write(c, path)
    report = validate_container(path, repo_root=repo)
    assert any("verification_tier" in v for v in report["violations"])


def test_invalid_tier_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "claim_container_x.json"
    c = _valid_container(repo)
    c["claims"][0]["verification_tier"] = "T7"
    _write(c, path)
    report = validate_container(path, repo_root=repo)
    assert any("T0..T6" in v for v in report["violations"]), report


def test_missing_evidence_file_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "claim_container_x.json"
    c = _valid_container(repo)
    c["claims"][0]["evidence"] = [{"path": "does_not_exist.pdf", "kind": "report"}]
    _write(c, path)
    report = validate_container(path, repo_root=repo)
    assert any("not found" in v for v in report["violations"]), report


def test_empty_claims_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "claim_container_x.json"
    c = _valid_container(repo)
    c["claims"] = []
    _write(c, path)
    report = validate_container(path, repo_root=repo)
    assert any("non-empty" in v for v in report["violations"]), report


def test_invalid_json_fails(tmp_path: Path) -> None:
    path = tmp_path / "claim_container_broken.json"
    path.write_text("{ not json", encoding="utf-8")
    report = validate_container(path)
    assert report["violation_count"] == 1


def test_validate_dir_reports_multiple_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    biz = repo / "artifacts" / "business"
    biz.mkdir(parents=True)
    _write(_valid_container(repo, "a_report.html"), biz / "claim_container_a.json")
    bad = _valid_container(repo, "b_report.html")
    bad["claims"][0]["verification_tier"] = "T9"
    _write(bad, biz / "claim_container_b.json")
    report = validate_dir(biz, repo_root=repo)
    assert report["violation_count"] == 1, report


def test_engine_has_emitter_wired() -> None:
    """SOE's outcome_engine.py defines the emitter and calls it from main()."""
    if not SOE_ENGINE.exists():
        pytest.skip(f"SOE engine not present ({SOE_ENGINE})")
    src = SOE_ENGINE.read_text(encoding="utf-8")
    assert "def emit_claim_container(" in src, "emit_claim_container missing"
    assert "emit_claim_container(args.client" in src, (
        "emitter must be called from main() (wire exists, not just a definition)"
    )
    # Contract fields must be present in the emitted object.
    for field in ("deliverable_id", "claim_id", "verification_tier", "evidence", "evaluated_at"):
        assert field in src, f"claim contract field '{field}' missing from emitter"
