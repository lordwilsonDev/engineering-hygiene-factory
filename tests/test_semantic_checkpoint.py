#!/usr/bin/env python3
"""Test for semantic checkpointing."""

import json
import time
from pathlib import Path
from semantic_checkpoint import create_checkpoint, CHECKPOINTS_DIR


def test_semantic_checkpoint_creates_distinct_files() -> None:
    initial_count = len(list(CHECKPOINTS_DIR.glob("*.json"))) if CHECKPOINTS_DIR.exists() else 0

    f1 = create_checkpoint()
    time.sleep(1.0)
    f2 = create_checkpoint()

    assert f1.exists()
    assert f2.exists()
    assert f1 != f2

    data1 = json.loads(f1.read_text(encoding="utf-8"))
    data2 = json.loads(f2.read_text(encoding="utf-8"))

    assert "content_hash" in data1
    assert "content_hash" in data2
    assert "timestamp" in data1
    assert "projects" in data1
    assert data1["content_hash"] != data2["content_hash"]

    new_count = len(list(CHECKPOINTS_DIR.glob("*.json")))
    assert new_count >= initial_count + 2
