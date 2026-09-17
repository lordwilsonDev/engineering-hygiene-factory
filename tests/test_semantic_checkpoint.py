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


def test_checkpoint_writes_on_claims_change(monkeypatch, tmp_path: Path) -> None:
    """Adding or modifying a claim triggers a new checkpoint."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1", "subject": "s1"}]}))
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "store")

    f1 = sc.create_checkpoint()
    assert f1 is not None
    h1 = json.loads(f1.read_text(encoding="utf-8"))["content_hash"]

    # Add a second claim -> semantic snapshot changes -> new checkpoint.
    claims.write_text(json.dumps({"claims": [
        {"claim_id": "c1", "subject": "s1"},
        {"claim_id": "c2", "subject": "s2"}
    ]}))
    f2 = sc.create_checkpoint()
    assert f2 is not None and f2 != f1
    assert json.loads(f2.read_text(encoding="utf-8"))["content_hash"] != h1

    # Modify a claim subject -> new checkpoint.
    claims.write_text(json.dumps({"claims": [
        {"claim_id": "c1", "subject": "modified"},
        {"claim_id": "c2", "subject": "s2"}
    ]}))
    f3 = sc.create_checkpoint()
    assert f3 is not None and f3 != f2

    # Remove a claim -> new checkpoint.
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1", "subject": "modified"}]}))
    f4 = sc.create_checkpoint()
    assert f4 is not None and f4 != f3


def test_checkpoint_skips_volatile_claim_timestamps(monkeypatch, tmp_path: Path) -> None:
    """Updating evaluated_at / generated_at in claims does NOT trigger a write."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": [
        {"claim_id": "c1", "subject": "s1", "evaluated_at": "2026-08-10T16:00:00Z"}
    ]}))
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "store")

    f1 = sc.create_checkpoint()
    assert f1 is not None
    store_size = len(list((tmp_path / "store").glob("*.json")))

    # Bump only the volatile timestamp -> no new write.
    claims.write_text(json.dumps({"claims": [
        {"claim_id": "c1", "subject": "s1", "evaluated_at": "2026-08-10T17:00:00Z"}
    ]}))
    f2 = sc.create_checkpoint()
    assert f2 is None
    assert len(list((tmp_path / "store").glob("*.json"))) == store_size

    # Bump generated_at too -> still no write.
    claims.write_text(json.dumps({"claims": [
        {"claim_id": "c1", "subject": "s1",
         "evaluated_at": "2026-08-10T17:00:00Z", "generated_at": "2026-08-10T18:00:00Z"}
    ]}))
    f3 = sc.create_checkpoint()
    assert f3 is None
    assert len(list((tmp_path / "store").glob("*.json"))) == store_size


def test_non_verified_evidence_recorded(monkeypatch, tmp_path: Path) -> None:
    """CONTESTED/REGRESSED/STALE project evidence is recorded in payload."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [
        {"project": "a", "state": "VERIFIED", "git_head": "abc123"},
        {"project": "b", "state": "STALE", "git_head": "def456", "release_verdict": "DEGRADED"},
    ]}))
    claims.write_text(json.dumps({"claims": []}))
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "store")

    f1 = sc.create_checkpoint()
    assert f1 is not None
    data = json.loads(f1.read_text(encoding="utf-8"))
    assert data["non_verified_evidence"] == {
        "b": {"state": "STALE", "git_head": "def456", "release_verdict": "DEGRADED"}
    }

    # Projects in dict form should also populate non_verified_evidence.
    status.write_text(json.dumps({
        "projects": {
            "a": {"state": "VERIFIED", "git_head": "abc"},
            "c": {"state": "CONTESTED", "git_head": "ghi", "release_verdict": "FAILING"},
        }
    }))
    f2 = sc.create_checkpoint()
    assert f2 is not None
    data = json.loads(f2.read_text(encoding="utf-8"))
    assert "c" in data["non_verified_evidence"]
    assert data["non_verified_evidence"]["c"]["state"] == "CONTESTED"


def test_resilience_to_missing_or_corrupt_files(monkeypatch, tmp_path: Path) -> None:
    """Missing or corrupted status/claims files do not crash checkpointing."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", tmp_path / "store")

    # Neither file exists yet -> still writes (empty state).
    f1 = sc.create_checkpoint()
    assert f1 is not None

    # Corrupt JSON in status -> graceful fallback, no crash. This DOES write
    # (rather than being change-gated away): an input that exists but cannot be
    # parsed is itself a state change — the snapshot records which input was
    # unreadable, so "no input yet" -> "status.json unreadable" is a real
    # transition. Treating it as an empty-but-identical state would let a
    # corruption event pass with no trace in the durable record.
    status.write_text("{not valid json")
    claims.write_text(json.dumps({"claims": []}))
    f2 = sc.create_checkpoint()
    assert f2 is not None
    assert json.loads(f2.read_text(encoding="utf-8"))["unreadable_inputs"] == ["status"]

    # Corrupt JSON in claims -> graceful fallback, no crash.
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text("[[BROKEN]")
    f3 = sc.create_checkpoint()
    assert f3 is not None

    # Corrupt checkpoint file in store -> latest_checkpoint_snapshot is resilient.
    (tmp_path / "store").mkdir(parents=True, exist_ok=True)
    corrupt = tmp_path / "store" / "bad.json"
    corrupt.write_text("{broken")
    assert sc.latest_checkpoint_snapshot() is None

    # Empty projects / zero claims -> still works.
    status.write_text(json.dumps({"projects": []}))
    claims.write_text(json.dumps({"claims": []}))
    f4 = sc.create_checkpoint()
    assert f4 is not None


def test_checkpoint_determinism(monkeypatch, tmp_path: Path) -> None:
    """Identical inputs produce identical checkpoint content and filename."""
    status = tmp_path / "status.json"
    claims = tmp_path / "claims.json"
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1"}]}))
    monkeypatch.setattr(sc, "STATUS_JSON", status)
    monkeypatch.setattr(sc, "CLAIMS_JSON", claims)
    store = tmp_path / "store"
    monkeypatch.setattr(sc, "CHECKPOINTS_DIR", store)

    # Fix the git head so the two writes are truly identical. Via monkeypatch
    # (not a raw assignment) so it is undone — a bare module-level lambda here
    # stayed installed for every test that ran afterwards in the process.
    import semantic_checkpoint as _sc
    monkeypatch.setattr(_sc, "get_factory_git_head", lambda: "fixed-head")

    f1 = sc.create_checkpoint()
    assert f1 is not None
    content1 = f1.read_text(encoding="utf-8")
    h1 = json.loads(content1)["content_hash"]

    # Identical state again -> skipped (no new file).
    f2 = sc.create_checkpoint()
    assert f2 is None

    # Re-create the checkpoint file by restoring identical status/claims ->
    # should produce the SAME content hash and SAME filename.
    status.write_text(json.dumps({"projects": [{"project": "a", "state": "VERIFIED"}]}))
    claims.write_text(json.dumps({"claims": [{"claim_id": "c1"}]}))
    # Remove the existing checkpoint so the next write is a fresh file with the
    # same content hash but we can still compare filenames.
    f1.unlink()
    f3 = sc.create_checkpoint()
    assert f3 is not None
    content3 = f3.read_text(encoding="utf-8")
    h3 = json.loads(content3)["content_hash"]
    # Deterministic: same inputs -> same hash.
    assert h3 == h1
    # Same hash -> same content-addressed filename suffix. The timestamp PREFIX
    # is volatile by design, so comparing whole names could never hold; the
    # suffix is the content id. (This line used to read `... or True`, which
    # passes unconditionally — it asserted nothing while claiming to check the
    # filename, so the hash rule it was meant to pin was never actually pinned.)
    assert f3.name.split("_", 1)[1] == f1.name.split("_", 1)[1]
    assert json.loads(content3)["non_verified_evidence"] == {}
