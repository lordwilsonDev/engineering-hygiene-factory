#!/usr/bin/env python3
"""semantic_checkpoint.py — snapshot semantic state across the constellation.

Creates an immutable, content-hashed JSON checkpoint under
artifacts/status/semantic_checkpoints/<iso-date>.json containing:
- timestamp
- factory_git_head
- project_states (from status.json)
- claims (from claims.json)
- non_verified_evidence (CONTESTED/REGRESSED/STALE projects + commit SHAs)
- content_hash (SHA256 digest of the semantic snapshot — a CONTENT id, so
  identical semantic state hashes identically; see _semantic_snapshot)
- unreadable_inputs (inputs that existed but could not be parsed)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Versioned by design: checkpoints are the anti-amnesia record (claims,
# contradictions, decisions across context compression) and must survive —
# they live OUTSIDE the gitignored artifacts/ tree so every snapshot is
# committed as evidence. artifacts/ is CI-regenerated scratch; checkpoints/ is
# durable ledger history.
#
# SEMANTIC_CHECKPOINT_DIR overrides the store (tests point it at a temp dir so
# the versioned history is never polluted by test runs).
CHECKPOINTS_DIR = Path(os.environ.get("SEMANTIC_CHECKPOINT_DIR") or (ROOT / "checkpoints" / "semantic"))
STATUS_JSON = ROOT / "artifacts" / "status" / "status.json"
CLAIMS_JSON = ROOT / "artifacts" / "status" / "claims.json"


def get_factory_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def _project_entries(status_data: dict) -> list[dict]:
    """`status.json`'s projects as a list of dicts, in either supported shape.

    List form is canonical (status_report.py emits it); the dict form
    (name -> info) is tolerated. Deliberately ONE normalizer used by both the
    snapshot and the non_verified_evidence collector: those two used to
    disagree about the dict form, and the disagreement silently dropped
    CONTESTED/REGRESSED/STALE evidence — the negative evidence this record
    exists to preserve.
    """
    projects = (status_data or {}).get("projects", {})
    if isinstance(projects, dict):
        return [{"project": name, **info}
                for name, info in projects.items() if isinstance(info, dict)]
    if isinstance(projects, list):
        return [info for info in projects if isinstance(info, dict)]
    return []


def _semantic_snapshot(status_data: dict, claims_data: object,
                       unreadable: tuple[str, ...] = ()) -> dict:
    """The parts of a checkpoint that carry semantic meaning.

    Timestamps, factory git HEAD, absolute repo paths, and evidence ages are
    volatile (they change every run and differ between local and CI) — they
    are excluded so two runs with the same semantic state hash identically.
    Change-gating on this snapshot is what keeps the versioned store a record
    of MEANINGFUL state, not a near-duplicate per run.

    `unreadable` names inputs that EXISTED but could not be parsed. It belongs
    to the snapshot because a corrupt status.json would otherwise project to
    the same snapshot as "no projects at all": the record would assert an
    empty constellation as fact rather than report that it could not read one,
    and a corruption event would leave no trace. Naming it also gives the
    recovery (file readable again) its own transition back.
    """
    stable_projects = []
    for p_info in _project_entries(status_data):
        p_name = p_info.get("project") or p_info.get("name")
        if not p_name:
            continue
        stable_projects.append({
            "project": p_name,
            "state": p_info.get("state") or p_info.get("verification_state"),
            "verification_tier": p_info.get("verification_tier"),
            "gate": p_info.get("gate"),
            "hygiene": p_info.get("hygiene"),
            "mutation_score_pct": p_info.get("mutation_score_pct"),
            "coverage_pct": p_info.get("coverage_pct"),
            "ci": p_info.get("ci"),
        })
    stable_projects.sort(key=lambda p: p["project"])

    # Normalize claims: strip the volatile evaluated_at/generated_at timestamps
    # (they change every run) and keep only the stable semantic fields, so the
    # snapshot is comparable across runs and environments.
    stable_claims = []
    raw_claims = claims_data.get("claims") if isinstance(claims_data, dict) else claims_data
    for c in raw_claims if isinstance(raw_claims, list) else []:
        if not isinstance(c, dict):
            continue
        stable_claims.append({k: c.get(k) for k in (
            "claim_id", "subject", "claim_type", "verification_tier", "verdict")})
    stable_claims.sort(key=lambda c: c.get("claim_id", ""))
    return {"projects": stable_projects, "claims": stable_claims,
            "unreadable": sorted(unreadable)}


def latest_checkpoint_snapshot() -> dict | None:
    """The stored semantic snapshot of the most recent checkpoint, if any."""
    if not CHECKPOINTS_DIR.is_dir():
        return None
    files = sorted(CHECKPOINTS_DIR.glob("*.json"))
    if not files:
        return None
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None
    return data.get("semantic_snapshot")


def create_checkpoint() -> Path | None:
    """Write a semantic checkpoint IF the semantic state changed; else skip.

    Returns the checkpoint path when written, or None when the state is
    unchanged since the last checkpoint (change-gated, so the versioned store
    records meaningful transitions instead of a near-duplicate per run).
    """
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    iso_date = datetime.now(timezone.utc).isoformat()

    # An input that exists but cannot be parsed is NOT the same as an absent
    # one: absent means "the ledger has not produced this yet", unparseable
    # means "something is wrong". Only the second is recorded (see
    # _semantic_snapshot).
    unreadable: list[str] = []
    status_data = {}
    if STATUS_JSON.exists():
        try:
            status_data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
        except Exception:
            unreadable.append("status")

    claims_data = []
    if CLAIMS_JSON.exists():
        try:
            claims_data = json.loads(CLAIMS_JSON.read_text(encoding="utf-8"))
        except Exception:
            unreadable.append("claims")

    snapshot = _semantic_snapshot(status_data, claims_data, tuple(unreadable))
    if snapshot == latest_checkpoint_snapshot():
        print("semantic checkpoint: state unchanged since last checkpoint — skipped")
        return None

    projects = status_data.get("projects", [])
    non_verified = {}
    for p_info in _project_entries(status_data):
        p_name = p_info.get("project") or p_info.get("name")
        if not p_name:
            continue
        state = p_info.get("state") or p_info.get("verification_state")
        if state in ("CONTESTED", "REGRESSED", "STALE"):
            non_verified[p_name] = {
                "state": state,
                "git_head": p_info.get("git_head"),
                "release_verdict": p_info.get("release_verdict"),
            }

    payload = {
        "timestamp": iso_date,
        "factory_git_head": get_factory_git_head(),
        # `projects` may be a list or a dict; anything else (e.g. null) must
        # not crash a module whose contract is "never fail the caller".
        "projects_count": len(projects) if isinstance(projects, (list, dict)) else 0,
        "projects": projects,
        "claims": claims_data,
        "non_verified_evidence": non_verified,
        "unreadable_inputs": unreadable,
        "semantic_snapshot": snapshot,
    }

    # The hash covers the SEMANTIC SNAPSHOT, not the payload. Hashing the whole
    # payload included `timestamp` (and environment-dependent project paths), so
    # identical content produced different hashes — the exact opposite of the
    # invariant _semantic_snapshot documents above — and the filename suffix
    # was a timestamp in disguise. Now the change-gate (`snapshot ==`) and the
    # id (`content_hash`) agree on what "content" means.
    # NOTE: checkpoints written before 2026-09-17 carry hashes from the old
    # rule. They are immutable history and are left as they are; the next real
    # state change writes the first content-addressed file.
    raw_bytes = json.dumps(snapshot, sort_keys=True).encode("utf-8")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    payload["content_hash"] = content_hash

    checkpoint_file = CHECKPOINTS_DIR / f"{ts_str}_{content_hash[:8]}.json"
    checkpoint_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"semantic checkpoint -> {checkpoint_file} (hash: {content_hash[:8]})")
    return checkpoint_file


if __name__ == "__main__":
    create_checkpoint()
