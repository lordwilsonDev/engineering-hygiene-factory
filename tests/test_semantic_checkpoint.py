#!/usr/bin/env python3
"""Tests for semantic checkpointing (change-gated, versioned store)."""

import json
from pathlib import Path

import semantic_checkpoint as sc


def test_checkpoint_writes_on_state_change(monkeypatch, tmp_path: Path) -> None:
    """A changed semantic state produces a new content-hashed checkpoint."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1"}]}))
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "store")

    f1 = sc.create_checkpoint()
    assert f1 is not None and f1.exists()

    data = json.loads(f1.read_text(encoding="utf-8"))
    assert "content_hash" in data
    assert "semantic_snapshot" in data
    assert data["semantic_snapshot"]["projects"] == [
        {"project": "a", "state": "VERIFIED",
         "verification_tier": None, "gate": None, "hygiene": None,
         "mutation_score_pct": None, "coverage_pct": None, "ci": None}
    ]

    # State change -> new checkpoint.
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "STALE"}]}))
    f2 = sc.create_checkpoint()
    assert f2 is not None and f2 != f1
    assert json.loads(f2.read_text(encoding="utf-8"))["content_hash"] != \
        json.loads(f1.read_text(encoding="utf-8"))["content_hash"]


def test_checkpoint_skips_unchanged_state(monkeypatch, tmp_path: Path) -> None:
    """Unchanged semantic state writes nothing (change-gated)."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": []}))
    store = tmp_path / "store"
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", store)

    f1 = sc.create_checkpoint()
    assert f1 is not None

    # Same state again -> skipped, no new file.
    f2 = sc.create_checkpoint()
    assert f2 is None
    assert len(list(store.glob("*.json"))) == 1

    # Volatile-only differences (timestamp/git HEAD/evidence age) do NOT
    # trigger a write — evidence_age_h is excluded from the semantic snapshot.
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED",
                                                "evidence_age_h": 99.9}]}))
    f3 = sc.create_checkpoint()
    assert f3 is None
    assert len(list(store.glob("*.json"))) == 1


def test_latest_checkpoint_snapshot_roundtrip(monkeypatch, tmp_path: Path) -> None:
    """latest_checkpoint_snapshot reads back the stored semantic snapshot."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "FAILING"}]}))
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1"}]}))
    store = tmp_path / "store"
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", store)

    f1 = sc.create_checkpoint()
    assert f1 is not None
    latest = sc.latest_checkpoint_snapshot()
    assert latest is not None
    assert latest["projects"][0]["state"] == "FAILING"
    # claims are normalized to stable fields (timestamps stripped)
    assert latest["claims"] == [{"claim_id": "c1", "subject": None,
                                  "claim_type": None, "verification_tier": None,
                                  "verdict": None}]

    # With no checkpoints yet, latest is None.
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "empty-store")
    assert sc.latest_checkpoint_snapshot() is None
