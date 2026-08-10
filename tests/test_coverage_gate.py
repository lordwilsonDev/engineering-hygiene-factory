#!/usr/bin/env python3
"""Tests for the coverage-floor gate added to run_factory.py.

Three pieces are pinned so the gate can't silently drift:
  1. load_suite_config parses coverage_floor/coverage_source and preserves
     them across the built-in-SUITE fallback (msb-v3's config-only suite.json).
  2. run_pytest measures coverage (--cov args) and parses coverage.py's
     TOTAL row into coverage_pct.
  3. assess_coverage's truth table: not configured -> None (never a fail),
     not measured -> False, below floor -> False, at/above floor -> True.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import run_factory as rf  # noqa: E402  (sys.path via root conftest.py)


# ── load_suite_config ─────────────────────────────────────────────────────────

def _write_suite(project: Path, cfg: dict) -> None:
    p = project / "scripts" / "hygiene"
    p.mkdir(parents=True)
    (p / "suite.json").write_text(json.dumps(cfg), encoding="utf-8")


def test_suite_config_coverage_parsed(tmp_path) -> None:
    _write_suite(tmp_path, {"coverage_floor": 0.6, "coverage_source": "buh_dna"})
    _, live, target, cov = rf.load_suite_config(tmp_path)
    assert cov == {"floor": 0.6, "source": "buh_dna"}
    assert live is True and target == "tests/"


def test_suite_config_coverage_without_experiments_falls_back_to_suite(tmp_path) -> None:
    """msb-v3's config-only suite.json: no experiments -> built-in SUITE, but
    the coverage config MUST survive the fallback (this is the regression the
    test exists for)."""
    _write_suite(tmp_path, {"coverage_floor": 0.65, "coverage_source": "src/msb_v3"})
    experiments, live, target, cov = rf.load_suite_config(tmp_path)
    assert experiments == rf.SUITE
    assert cov == {"floor": 0.65, "source": "src/msb_v3"}
    assert live is True and target == "tests/"


def test_suite_config_no_coverage_default(tmp_path) -> None:
    _write_suite(tmp_path, {"experiments": {"x": {"skill": "s", "runner": "r.py"}}})
    _, _, _, cov = rf.load_suite_config(tmp_path)
    assert cov == {"floor": 0.0, "source": None}


def test_suite_config_no_suite_file_default(tmp_path) -> None:
    experiments, live, target, cov = rf.load_suite_config(tmp_path)
    assert experiments == rf.SUITE
    assert cov == {"floor": 0.0, "source": None}
    assert live is True and target == "tests/"


# ── run_pytest (coverage measurement + TOTAL parse) ───────────────────────────

def _fake_proc(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr="")


def test_run_pytest_parses_total_line(tmp_path, monkeypatch) -> None:
    out = ("some test output\n"
           "100 passed in 1.2s\n"
           "Name       Stmts   Miss  Cover\n"
           "app.py       100     20    80%\n"
           "TOTAL        100     20    80%\n")
    monkeypatch.setattr(rf, "_spawn", lambda *a, **k: _fake_proc(out))
    res = rf.run_pytest(tmp_path, coverage={"floor": 0.5, "source": "app"})
    assert res["passed"] is True
    assert res["coverage_pct"] == 80.0
    assert res["coverage_source"] == "app"


def test_run_pytest_adds_cov_args_for_multiple_sources(tmp_path, monkeypatch) -> None:
    seen: dict = {}

    def _spy(args, **kw):
        seen["args"] = list(args)
        return _fake_proc("1 passed\nTOTAL 10 0 100%\n")

    monkeypatch.setattr(rf, "_spawn", _spy)
    rf.run_pytest(tmp_path, coverage={"floor": 0.5, "source": "a,b c"})
    assert "--cov" in seen["args"]
    assert "a" in seen["args"] and "b c" in seen["args"]
    assert "--cov-report=term" in seen["args"]


def test_run_pytest_without_coverage_no_cov_args(tmp_path, monkeypatch) -> None:
    seen: dict = {}

    def _spy(args, **kw):
        seen["args"] = list(args)
        return _fake_proc("1 passed\n")

    monkeypatch.setattr(rf, "_spawn", _spy)
    res = rf.run_pytest(tmp_path)
    assert "--cov" not in seen["args"]
    assert res.get("coverage_pct") is None


def test_run_pytest_no_total_line_means_none(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(rf, "_spawn", lambda *a, **k: _fake_proc("1 passed\n"))
    res = rf.run_pytest(tmp_path, coverage={"floor": 0.5, "source": "app"})
    assert res.get("coverage_pct") is None


# ── assess_coverage truth table ───────────────────────────────────────────────

def test_assess_not_configured_is_none() -> None:
    assert rf.assess_coverage({"passed": True}, None) == {
        "met": None, "detail": "coverage gate not configured"}
    assert rf.assess_coverage({"passed": True}, {"floor": 0.5, "source": None})["met"] is None


def test_assess_not_measured_is_false() -> None:
    res = rf.assess_coverage({"passed": True}, {"floor": 0.5, "source": "app"})
    assert res["met"] is False
    assert "not measured" in res["detail"]


def test_assess_below_floor_is_false() -> None:
    res = rf.assess_coverage({"passed": True, "coverage_pct": 40.0},
                             {"floor": 0.5, "source": "app"})
    assert res["met"] is False
    assert "40.0% vs floor 50%" in res["detail"]


def test_assess_at_floor_is_true() -> None:
    res = rf.assess_coverage({"passed": True, "coverage_pct": 50.0},
                             {"floor": 0.5, "source": "app"})
    assert res["met"] is True


def test_assess_above_floor_is_true() -> None:
    res = rf.assess_coverage({"passed": True, "coverage_pct": 91.0},
                             {"floor": 0.9, "source": "app"})
    assert res["met"] is True


def test_assess_zero_source_is_none() -> None:
    assert rf.assess_coverage({"passed": True}, {"floor": 0.0, "source": ""})["met"] is None
