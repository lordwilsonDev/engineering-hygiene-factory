#!/usr/bin/env python3
"""T6 FORMAL pathway guard (blueprint P3).

T6 FORMAL is the only tier no constellation repo reaches today, and it must
stay that way unless REAL formal-verification evidence appears. These tests
pin the guard so the pathway cannot be stumbled into:

1. An ordinary repo — even one with a perfect gate, passing pytest, live
   auth, a passing hygiene suite, and mutation >= 50% — caps at T5
   ADVERSARIAL. Running tests is not formal verification.
2. T6 unlocks ONLY via a valid artifacts/hygiene/formal_verification.json
   artifact: schema-conformant, result PASS, hashed artifact bindings.
3. Broken formal artifacts fail closed: malformed JSON, missing fields, a
   non-PASS result, or short/absent hashes never buy a higher tier.
"""

from __future__ import annotations

import json
from pathlib import Path

import status_report as sr  # noqa: E402  (sys.path via root conftest.py)


def _gate_pass() -> dict:
    return {
        "RELEASE_VERDICT": {"release_verdict": "PASS", "unresolved_unknowns": []},
        "VERIFICATION": {
            "git_head": "a" * 40,
            "pytest": {"passed": True, "summary": "123 passed"},
            "live_auth": {"verified": True},
            "coverage": {"configured": True, "pct": 92.0, "floor_pct": 90.0},
        },
    }


def _valid_formal_artifact() -> dict:
    return {
        "tool": "py_model_check",
        "technique": "bounded model check",
        "claims": ["claim:state_machine:invariant"],
        "result": "PASS",
        "artifact_hashes": {"src/state_machine.py": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"},
    }


def test_full_green_repo_caps_at_t5() -> None:
    """Perfect ordinary evidence must never reach T6."""
    tier = sr.verification_tier(_gate_pass(), True, True, "pass", 87.0, formal=False)
    assert tier == "T5 ADVERSARIAL", tier


def test_valid_formal_artifact_unlocks_t6() -> None:
    tier = sr.verification_tier(_gate_pass(), True, True, "pass", 87.0, formal=True)
    assert tier == "T6 FORMAL", tier


def test_formal_without_tests_stays_below() -> None:
    """A formal artifact with NO test evidence at all never lifts above T4."""
    tier = sr.verification_tier(_gate_pass(), False, True, "pass", None, formal=True)
    assert tier == "T4 INTEGRATED", tier


def test_formal_without_hygiene_stays_below() -> None:
    """A formal artifact with a failing hygiene suite never reaches T6.

    Mutation evidence (>=50%) legitimately lifts to T5 even when the hygiene
    suite is red, because mutation evidence presupposes the tests ran — but
    the T6 gate additionally requires hygiene==pass, so formal never wins.
    """
    tier = sr.verification_tier(_gate_pass(), True, True, "fail", None, formal=True)
    assert tier == "T3 EXECUTED", tier


def test_missing_artifact_is_false(tmp_path: Path) -> None:
    assert sr.formal_verification(tmp_path) is False


def test_malformed_artifact_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    path.write_text("{ not json", encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_missing_fields_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    del artifact["technique"]
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_non_pass_result_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    artifact["result"] = "FAIL"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_short_hashes_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    artifact["artifact_hashes"] = {"src/state_machine.py": "abc"}  # too short
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_non_sha_digest_fails_closed(tmp_path: Path) -> None:
    """A 64-char but non-hex digest is not a real hash binding."""
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    artifact["artifact_hashes"] = {"src/state_machine.py": "z" * 64}  # not hex
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_empty_claims_fail_closed(tmp_path: Path) -> None:
    """A formal artifact that claims nothing was checked cannot unlock T6."""
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    artifact["claims"] = []
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_blank_tool_fails_closed(tmp_path: Path) -> None:
    """An unnamed tool/technique is not a formal method."""
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    artifact = _valid_formal_artifact()
    artifact["tool"] = "   "
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is False


def test_valid_artifact_is_true(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "hygiene" / sr.FORMAL_ARTIFACT
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_valid_formal_artifact()), encoding="utf-8")
    assert sr.formal_verification(tmp_path) is True
