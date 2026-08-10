#!/usr/bin/env python3
"""semantic_checkpoint.py — snapshot semantic state across the constellation.

Creates an immutable, content-hashed JSON checkpoint under
artifacts/status/semantic_checkpoints/<iso-date>.json containing:
- timestamp
- factory_git_head
- project_states (from status.json)
- claims (from claims.json)
- non_verified_evidence (CONTESTED/REGRESSED/STALE projects + commit SHAs)
- content_hash (SHA256 digest of payload)
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


def _semantic_snapshot(status_data: dict, claims_data: object) -> dict:
    """The parts of a checkpoint that carry semantic meaning.

    Timestamps, factory git HEAD, absolute repo paths, and evidence ages are
    volatile (they change every run and differ between local and CI) — they
    are excluded so two runs with the same semantic state hash identically.
    Change-gating on this snapshot is what keeps the versioned store a record
    of MEANINGFUL state, not a near-duplicate per run.
    """
    projects = status_data.get("projects", {})
    if isinstance(projects, dict):
        projects = [
            {"project": p_name, **p_info}
            for p_name, p_info in projects.items()
            if isinstance(p_info, dict)
        ]
    stable_projects = []
    for p_info in projects if isinstance(projects, list) else []:
        if not isinstance(p_info, dict):
            continue
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
    return {"projects": stable_projects, "claims": stable_claims}


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

    status_data = {}
    if STATUS_JSON.exists():
        try:
            status_data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    claims_data = []
    if CLAIMS_JSON.exists():
        try:
            claims_data = json.loads(CLAIMS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    snapshot = _semantic_snapshot(status_data, claims_data)
    if snapshot == latest_checkpoint_snapshot():
        print("semantic checkpoint: state unchanged since last checkpoint — skipped")
        return None

    projects = status_data.get("projects", [])
    non_verified = {}
    for p_info in projects if isinstance(projects, list) else []:
        if not isinstance(p_info, dict):
            continue
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
        "projects_count": len(projects) if isinstance(projects, list) else len(projects),
        "projects": projects,
        "claims": claims_data,
        "non_verified_evidence": non_verified,
        "semantic_snapshot": snapshot,
    }

    raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    payload["content_hash"] = content_hash

    checkpoint_file = CHECKPOINTS_DIR / f"{ts_str}_{content_hash[:8]}.json"
    checkpoint_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"semantic checkpoint -> {checkpoint_file} (hash: {content_hash[:8]})")
    return checkpoint_file


if __name__ == "__main__":
    create_checkpoint()
