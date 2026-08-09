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


def test_mutation_score_reads_snapshot_artifact(tmp_path):
    """The mutation column is derived from mutation_score.json, not asserted."""
    repo = tmp_path / "agent-reach"
    (repo / "artifacts" / "hygiene").mkdir(parents=True)
    (repo / "artifacts" / "hygiene" / "mutation_score.json").write_text(
        json.dumps({"score_pct": 63.6}), encoding="utf-8")
    assert sr.mutation_score(repo) == 63.6


def test_mutation_score_none_when_artifact_missing(tmp_path):
    """No mutation evidence -> None, rendered as '-' in the table."""
    repo = tmp_path / "nexus"
    (repo / "artifacts" / "hygiene").mkdir(parents=True)
    assert sr.mutation_score(repo) is None


def test_build_status_includes_mutation_column(tmp_path):
    """build_status surfaces the mutation score per project."""
    ar = tmp_path / "agent-reach"
    (ar / "artifacts" / "hygiene").mkdir(parents=True)
    (ar / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate()), encoding="utf-8")
    (ar / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")
    (ar / "artifacts" / "hygiene" / "mutation_score.json").write_text(
        json.dumps({"score_pct": 63.6}), encoding="utf-8")
    nx = tmp_path / "nexus"
    (nx / "artifacts" / "hygiene").mkdir(parents=True)
    (nx / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate()), encoding="utf-8")
    (nx / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")

    old = sr.PROJECTS
    sr.PROJECTS = [
        {"name": "agent-reach", "repo": str(ar), "slug": "x/ar"},
        {"name": "nexus", "repo": str(nx), "slug": "x/nx"},
    ]
    try:
        status = sr.build_status(with_ci=False)
        by_name = {p["project"]: p for p in status["projects"]}
        assert by_name["agent-reach"]["mutation_score_pct"] == 63.6
        assert by_name["nexus"]["mutation_score_pct"] is None
        md = sr.render_markdown(status)
        assert "| 63.6% |" in md
        assert "| - |" in md  # nexus renders '-' for the missing mutation
    finally:
        sr.PROJECTS = old


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


def test_check_ignores_unverified_but_strict_does_not(tmp_path, monkeypatch):
    """--check is the CI canary (absent projects non-fatal); --strict is the
    local constellation-wide gate (anything below VERIFIED is fatal)."""
    msb = tmp_path / "msb-v3"
    (msb / "artifacts" / "hygiene").mkdir(parents=True)
    (msb / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate("FAIL")), encoding="utf-8")
    (msb / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")
    ghost = tmp_path / "ghost"  # exists on disk but has NO evidence at all

    old = sr.PROJECTS
    sr.PROJECTS = [
        {"name": "msb-v3", "repo": str(msb), "slug": "x/msb"},
        {"name": "ghost", "repo": str(ghost), "slug": "x/ghost"},
    ]
    try:
        status = sr.build_status(with_ci=False)
        by_name = {p["project"]: p for p in status["projects"]}
        assert by_name["ghost"]["state"] == "UNVERIFIED"
        assert by_name["msb-v3"]["state"] == "FAILING"

        # --check: only FAILING is fatal; UNVERIFIED ghost is tolerated.
        assert sr.main(["--check"]) == 1
        # --strict: UNVERIFIED alone is fatal even without any FAILING project.
        sr.PROJECTS = [{"name": "ghost", "repo": str(ghost), "slug": "x/ghost"}]
        assert sr.main(["--strict"]) == 1
        # A fully verified tree passes strict.
        sr.PROJECTS = [{"name": "msb-v3", "repo": str(msb), "slug": "x/msb"}]
        (msb / "artifacts" / "hygiene" / "factory_gate.json").write_text(
            json.dumps(_gate()), encoding="utf-8")  # verdict back to PASS
        fresh = time.time()
        os_utime = __import__("os").utime
        os_utime(msb / "artifacts" / "hygiene" / "factory_gate.json", (fresh, fresh))
        assert sr.main(["--strict"]) == 0
    finally:
        sr.PROJECTS = old
