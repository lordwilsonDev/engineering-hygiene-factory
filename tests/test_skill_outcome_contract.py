#!/usr/bin/env python3
"""Skill-outcome contract enforcement (blueprint P2.3).

The blueprint's 2.3 contract: a state-mutating skill is judged by its VERIFIED
OUTCOME, not by process exit code. For skills whose emitter is a thin CLI
wrapper, the enforceable, zero-spend check is:

1. The emitter (`emit_outcome` in the skill's wrapper) exists and writes the
   contract shape: {skill, task, outcome, evidence_paths, verification, ts}.
2. The emitter is actually CALLED on the state-mutating / verification paths
   (search, freshness, reindex) — not defined and forgotten.
3. The skill's SKILL.md declares the contract (the standing instruction an
   agent reads when loading the skill).

Reference implementation: vault-check-first (state-mutating: --reindex
spawns a ~10min reindex) whose emitter lives in ~/bin/vault-check.py.

This test SKIPS when the skill tree is absent (e.g. factory checked out alone
in CI), mirroring the d03/d05/d07 convention.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REQUIRED_FIELDS = {"skill", "task", "outcome", "evidence_paths", "verification", "ts"}

_DEFAULT_WRAPPER = Path.home() / "bin" / "vault-check.py"
WRAPPER = Path(os.environ.get("VAULT_CHECK_WRAPPER", _DEFAULT_WRAPPER))
_DEFAULT_SKILL_DIR = Path.home() / ".hermes" / "skills" / "vault-check-first"
SKILL_DIR = Path(os.environ.get("VAULT_CHECK_SKILL_DIR", _DEFAULT_SKILL_DIR))


def _load_wrapper_module() -> object:
    import importlib.util

    spec = importlib.util.spec_from_file_location("vault_check_under_test", WRAPPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_emitter_writes_contract_shape(tmp_path: Path) -> None:
    """emit_outcome writes the full contract shape to the skill outcomes dir."""
    if not WRAPPER.exists():
        pytest.skip(f"skill wrapper not present ({WRAPPER}); set VAULT_CHECK_WRAPPER")
    module = _load_wrapper_module()
    emit = getattr(module, "emit_outcome", None)
    assert callable(emit), "emit_outcome missing from skill wrapper"

    # Redirect the outcome dir to a temp path so the test never writes into
    # the versioned skill tree.
    module.OUTCOME_DIR = tmp_path
    emit("search", "ok", "hermetic contract check", evidence_paths=["a.md", "b.md"])

    files = sorted(tmp_path.glob("*.json"))
    assert len(files) == 1, f"expected exactly 1 outcome file, got {len(files)}"
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert REQUIRED_FIELDS <= set(record), (
        f"missing contract fields: {REQUIRED_FIELDS - set(record)}"
    )
    assert record["skill"] == "vault-check-first"
    assert record["task"] == "search"
    assert record["outcome"] == "ok"
    assert record["evidence_paths"] == ["a.md", "b.md"]
    assert isinstance(record["verification"], str) and record["verification"]
    assert record["ts"], "ts must be a UTC timestamp string"


def test_emitter_wired_to_state_mutating_paths() -> None:
    """The emitter is called on the real paths, not defined and forgotten."""
    if not WRAPPER.exists():
        pytest.skip(f"skill wrapper not present ({WRAPPER}); set VAULT_CHECK_WRAPPER")
    src = WRAPPER.read_text(encoding="utf-8")
    # Every state-mutating / verification-relevant operation must call the
    # emitter: search (service_unreachable), reindex, freshness.
    assert src.count("emit_outcome(") >= 4, (
        "emit_outcome is under-wired: expected calls for service_unreachable, "
        "reindex_dispatched, qdrant_unreachable, and freshness verdicts"
    )
    for marker in ("--reindex", "--fresh"):
        assert marker in src, f"state-mutating path {marker} missing from wrapper"


def test_skill_documents_the_contract() -> None:
    """The skill's SKILL.md declares the outcome contract agents must honor."""
    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.exists():
        pytest.skip(f"skill SKILL.md not present ({skill_md})")
    text = skill_md.read_text(encoding="utf-8")
    assert "skill-outcome" in text.lower(), (
        "SKILL.md must declare the skill-outcome contract (see "
        "'Skill-outcome contract' section)"
    )
    # The contract must pin the field names so an agent knows what to emit.
    for field in ("verification", "evidence_paths", "outcome"):
        assert field in text, f"contract field '{field}' not documented in SKILL.md"
