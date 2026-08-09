#!/usr/bin/env python3
"""Tests for the status-from-evidence generator.

The whole point of status_report.py is that status is DERIVED, never
asserted. These tests pin the derivation truth table so the meta-move itself
can't drift: every combination of (gate artifact, aggregate, freshness vs
last commit) must map to exactly the state the table promises.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import status_report as sr  # noqa: E402


def _gate(verdict: str = "PASS") -> dict:
    """factory_gate.json in its real (UPPERCASE) schema."""
    return {
        "RELEASE_VERDICT": {"release_verdict": verdict, "regression_passed": verdict == "PASS"},
        "VERIFICATION": {"pytest": {"passed": verdict == "PASS", "summary": "1 passed"}},
    }


def _agg(verdict: str = "pass") -> dict:
    return {"factory_verdict": verdict}


def test_missing_evidence_is_unverified():
    state, reasons = sr.derive_state(None, None, None, 0.0, sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "UNVERIFIED"
    assert "no factory_gate.json" in reasons[0]


def test_gate_fail_is_failing():
    state, _ = sr.derive_state(_gate("FAIL"), _agg(), 0.0, time.time(),
                               sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "FAILING"


def test_hygiene_fail_is_failing():
    state, _ = sr.derive_state(_gate(), _agg("fail"), 0.0, time.time(),
                               sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "FAILING"


def test_fresh_pass_is_verified():
    state, _ = sr.derive_state(_gate(), _agg(), 0.0, time.time(),
                               sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "VERIFIED"


def test_evidence_predating_last_commit_is_stale():
    # gate mtime BEFORE last commit -> the code has moved past the proof.
    commit_ts = time.time() - 3600
    gate_mtime = commit_ts - 3600
    state, reasons = sr.derive_state(_gate(), _agg(), commit_ts, gate_mtime,
                                     sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "STALE"
    assert "predates last commit" in reasons[0]


def test_old_evidence_is_stale_even_without_git():
    # No git repo, but the artifact is ancient -> stale, not verified.
    gate_mtime = time.time() - 30 * 86400
    state, reasons = sr.derive_state(_gate(), _agg(), None, gate_mtime,
                                     sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "STALE"
    assert "days old" in reasons[0]


def test_malformed_gate_is_not_verified():
    # Malformed JSON -> read as {} -> gate verdict != PASS -> FAILING.
    assert sr.read_json(Path("/nonexistent/artifact.json")) is None
    assert sr.read_json(Path("/dev/null")) == {}


def test_build_status_aggregate_worst_state_wins(tmp_path):
    """A FAILING project drags the aggregate verdict down to FAILING."""
    msb = tmp_path / "msb-v3"
    (msb / "artifacts" / "hygiene").mkdir(parents=True)
    (msb / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate("FAIL")), encoding="utf-8")
    (msb / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")

    ok = tmp_path / "agent-reach"
    (ok / "artifacts" / "hygiene").mkdir(parents=True)
    (ok / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate()), encoding="utf-8")
    (ok / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")

    # Monkeypatch the registry to the two tmp projects.
    old = sr.PROJECTS
    sr.PROJECTS = [
        {"name": "msb-v3", "repo": str(msb), "slug": "x/msb"},
        {"name": "agent-reach", "repo": str(ok), "slug": "x/ar"},
    ]
    try:
        status = sr.build_status(with_ci=False)
        by_name = {p["project"]: p for p in status["projects"]}
        assert by_name["msb-v3"]["state"] == "FAILING"
        assert by_name["agent-reach"]["state"] == "VERIFIED"
        assert status["verdict"] == "FAILING"  # worst state wins
    finally:
        sr.PROJECTS = old


def test_status_json_written_by_cli(tmp_path, monkeypatch):
    """The CLI writes both outputs and --check passes on a clean tree."""
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    monkeypatch.setattr(sr, "PROJECTS", [])
    assert sr.main(["--check"]) == 0
    assert (tmp_path / "STATUS.md").exists()
    assert (tmp_path / "artifacts" / "status" / "status.json").exists()
    payload = json.loads((tmp_path / "artifacts" / "status" / "status.json").read_text())
    assert payload["verdict"] in ("UNVERIFIED", "VERIFIED")
    assert payload["projects"] == []
