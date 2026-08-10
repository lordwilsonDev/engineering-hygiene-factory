#!/usr/bin/env python3
"""Tests for the status-from-evidence generator.

The whole point of status_report.py is that status is DERIVED, never
asserted. These tests pin the derivation truth table so the meta-move itself
can't drift: every combination of (gate artifact, aggregate, freshness vs
last commit) must map to exactly the state the table promises.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import status_report as sr  # noqa: E402  (sys.path via root conftest.py)


def _git(repo: Path, *args: str) -> None:
    """Run a git command inside the test repo, configured for CI machines."""
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True, timeout=30)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q")
    return repo


def _plant_gate(repo: Path, verdict: str = "PASS") -> Path:
    d = repo / "artifacts" / "hygiene"
    d.mkdir(parents=True)
    gate = d / "factory_gate.json"
    gate.write_text(json.dumps(_gate(verdict)), encoding="utf-8")
    (d / "hygiene_aggregate.json").write_text(
        json.dumps({"factory_verdict": "pass"}), encoding="utf-8")
    return gate


def _gate(verdict: str = "PASS", coverage: dict | None = None) -> dict:
    """factory_gate.json in its real (UPPERCASE) schema."""
    return {
        "RELEASE_VERDICT": {"release_verdict": verdict, "regression_passed": verdict == "PASS"},
        "VERIFICATION": {
            "pytest": {"passed": verdict == "PASS", "summary": "1 passed"},
            **({"coverage": coverage} if coverage is not None else {}),
        },
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


def test_gate_coverage_parses_verification_block():
    """The coverage column is derived from VERIFICATION.coverage, not asserted."""
    assert sr.gate_coverage(None) == (None, None)
    assert sr.gate_coverage(_gate()) == (None, None)  # no coverage block -> None
    gate = _gate(coverage={"configured": True, "pct": 71.0, "floor_pct": 65.0})
    assert sr.gate_coverage(gate) == (71.0, 65.0)
    # configured but unmeasured -> pct None, floor kept
    gate2 = _gate(coverage={"configured": True, "pct": None, "floor_pct": 50.0})
    assert sr.gate_coverage(gate2) == (None, 50.0)


def test_build_status_surfaces_coverage_column(tmp_path):
    """build_status + markdown render the measured/floor coverage."""
    repo = tmp_path / "msb-v3"
    (repo / "artifacts" / "hygiene").mkdir(parents=True)
    (repo / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate(coverage={"configured": True, "pct": 71.0, "floor_pct": 65.0})),
        encoding="utf-8")
    (repo / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")

    old = sr.PROJECTS
    sr.PROJECTS = [{"name": "msb-v3", "repo": str(repo), "slug": "x/msb"}]
    try:
        status = sr.build_status(with_ci=False)
        entry = status["projects"][0]
        assert entry["coverage_pct"] == 71.0
        assert entry["coverage_floor_pct"] == 65.0
        md = sr.render_markdown(status)
        assert "| 71.0%/65% |" in md  # measured/floor cell
    finally:
        sr.PROJECTS = old


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


def test_last_commit_time_excludes_evidence_commits(tmp_path):
    """Committing gate evidence must not advance the freshness clock — STALE
    means "code moved past the proof", not "proof was versioned" (the
    circularity that made committed evidence eternally STALE)."""
    repo = _make_repo(tmp_path)
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "code")
    code_ts = sr.last_commit_time(repo)

    gate = _plant_gate(repo)
    _git(repo, "add", "artifacts")
    _git(repo, "commit", "-q", "-m", "evidence")

    # The evidence-only commit must NOT move the freshness clock.
    assert sr.last_commit_time(repo) == code_ts


def test_evidence_commit_keeps_repo_verified(tmp_path, monkeypatch):
    """End-to-end: code commit -> gate runs -> evidence committed must stay
    VERIFIED (the exact flow that used to flip everything STALE)."""
    repo = _make_repo(tmp_path)
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "code")
    _plant_gate(repo)
    _git(repo, "add", "artifacts")
    _git(repo, "commit", "-q", "-m", "evidence")

    old = sr.PROJECTS
    sr.PROJECTS = [{"name": "p", "repo": str(repo), "slug": "x/p"}]
    try:
        status = sr.build_status(with_ci=False)
        assert status["projects"][0]["state"] == "VERIFIED"
        assert status["projects"][0]["stale_after_last_commit"] is False
    finally:
        sr.PROJECTS = old


def test_code_commit_after_gate_is_stale(tmp_path, monkeypatch):
    """The flip side: a REAL code commit after the gate still reads STALE.

    Deterministic by construction: the gate artifact mtime is pinned to a
    known-past timestamp with os.utime, so the subsequent code commit (whose
    timestamp is now) is guaranteed newer — no sleeps, no clock races."""
    repo = _make_repo(tmp_path)
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "code")
    gate = _plant_gate(repo)
    _git(repo, "add", "artifacts")
    _git(repo, "commit", "-q", "-m", "evidence")

    # Pin the gate to a fixed past mtime, then move real code past the proof.
    past = time.time() - 3600
    os.utime(gate, (past, past))
    (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "more code")

    state, reasons = sr.derive_state(
        _gate(), {"factory_verdict": "pass"},
        sr.last_commit_time(repo), gate.stat().st_mtime,
        sr.DEFAULT_STALE_DAYS * 86400)
    assert state == "STALE"
    assert "predates last commit" in reasons[0]


def test_repo_path_relative_resolves_under_msb_status_home(tmp_path, monkeypatch):
    """Bare-name repos resolve under MSB_STATUS_HOME (CI checkout workspace),
    while absolute paths (and test overrides) win as-is."""
    old = sr.PROJECTS
    sr.PROJECTS = [
        {"name": "nexus", "repo": "nexus", "slug": "x/nx"},            # relative
        {"name": "abs", "repo": str(tmp_path / "abs"), "slug": "x/a"},  # absolute
    ]
    try:
        monkeypatch.setenv("MSB_STATUS_HOME", str(tmp_path))
        assert sr.repo_path("nexus") == tmp_path / "nexus"
        assert sr.repo_path("abs") == tmp_path / "abs"
        monkeypatch.delenv("MSB_STATUS_HOME")
        # Default (no env): relative name resolves under ~ (unchanged behavior).
        assert sr.repo_path("nexus") == Path.home() / "nexus"
    finally:
        sr.PROJECTS = old


def test_repo_root_empty_env_falls_back_to_home(tmp_path, monkeypatch):
    """MSB_STATUS_HOME set-but-empty must not rebase repos onto cwd."""
    monkeypatch.setenv("MSB_STATUS_HOME", "   ")
    assert sr.repo_root() == Path.home()
    monkeypatch.setenv("MSB_STATUS_HOME", "")
    assert sr.repo_root() == Path.home()
    monkeypatch.setenv("MSB_STATUS_HOME", str(tmp_path))
    assert sr.repo_root() == tmp_path


def test_status_main_warns_unknown_only_names(tmp_path, monkeypatch, capsys):
    """A typo in --only must be loud, never a silently-shrunk gate."""
    stub = {"generated_at": "x", "generator": "g", "stale_after_days": 7,
            "verdict": "VERIFIED", "projects": []}
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    monkeypatch.setattr(sr, "PROJECTS", [{"name": "msb-v3", "repo": "msb-v3",
                                          "slug": "x/m"}])
    monkeypatch.setattr(sr, "build_status", lambda **kw: stub)
    assert sr.main(["--only", "msb-v3,nexu"]) == 0
    err = capsys.readouterr().err
    assert "nexu" in err and "not in PROJECTS" in err


def test_build_status_only_scopes_evaluation(tmp_path, monkeypatch):
    """`only` evaluates exactly the named projects, so --strict can gate the
    repos CI has checked out without tripping on absent-evidence projects
    that are covered by their own workflows."""
    ok = tmp_path / "ok"
    (ok / "artifacts" / "hygiene").mkdir(parents=True)
    (ok / "artifacts" / "hygiene" / "factory_gate.json").write_text(
        json.dumps(_gate()), encoding="utf-8")
    (ok / "artifacts" / "hygiene" / "hygiene_aggregate.json").write_text(
        json.dumps(_agg()), encoding="utf-8")
    bad = tmp_path / "bad"  # exists but has NO evidence -> UNVERIFIED

    old = sr.PROJECTS
    sr.PROJECTS = [
        {"name": "ok", "repo": str(ok), "slug": "x/ok"},
        {"name": "bad", "repo": str(bad), "slug": "x/bad"},
    ]
    try:
        status = sr.build_status(with_ci=False)
        by_name = {p["project"]: p for p in status["projects"]}
        assert by_name["ok"]["state"] == "VERIFIED"
        assert by_name["bad"]["state"] == "UNVERIFIED"
        # Scoped: only ok is evaluated -> aggregate VERIFIED (strict-safe).
        scoped = sr.build_status(with_ci=False, only=["ok"])
        assert [p["project"] for p in scoped["projects"]] == ["ok"]
        assert scoped["verdict"] == "VERIFIED"
        # Scoped to bad: UNVERIFIED -> strict would fail (correctly).
        scoped_bad = sr.build_status(with_ci=False, only=["bad"])
        assert scoped_bad["verdict"] == "UNVERIFIED"
    finally:
        sr.PROJECTS = old


def test_status_main_passes_only_to_build_status(tmp_path, monkeypatch):
    """--only a,b threads through main() into build_status."""
    seen: dict = {}
    stub = {"generated_at": "x", "generator": "g", "stale_after_days": 7,
            "verdict": "VERIFIED", "projects": []}
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    monkeypatch.setattr(sr, "PROJECTS", [])
    monkeypatch.setattr(sr, "build_status",
                        lambda **kw: seen.update(kw) or stub)
    assert sr.main(["--only", "msb-v3,nexus"]) == 0
    assert seen.get("only") == ["msb-v3", "nexus"]


def test_check_ignores_unverified_but_strict_does_not(tmp_path, monkeypatch):
    """--check is the CI canary (absent projects non-fatal); --strict is the
    local constellation-wide gate (anything below VERIFIED is fatal)."""
    # Hermetic: main() writes STATUS.md/status.json under ROOT — pin it to the
    # test tree so the suite never clobbers the factory's real status output.
    monkeypatch.setattr(sr, "ROOT", tmp_path)
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
