#!/usr/bin/env python3
"""Tests locking the zero-spend canary's ENFORCEMENT property.

`run_factory.py --self-test` proves three boundaries (paid credentials never
reach subprocesses; MCP_BRIDGE_SECRET always does; the in-process live-auth
probe carries the internal secret). These tests make the enforcement itself
reproducible: if `_spawn` — the single choke point both gate legs use — ever
stops scrubbing, `self_test()` MUST return 1. That property lives in tests,
not just in a session log.
"""

import os
import subprocess

import run_factory as rf  # noqa: E402  (sys.path via root conftest.py)


def _leaky_spawn(args, project=None, timeout=900):
    """The bug class the canary exists to catch: ambient env, unscrubbed."""
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, env=os.environ.copy())


def test_leaky_spawn_fails_self_test():
    """If _spawn leaks the ambient env, the canary must fail (rc=1).

    This is the load-bearing assertion: it proves the child leg of
    `self_test()` actually inspects what a spawned subprocess receives, so
    removing the scrub from the choke point cannot go unnoticed.
    """
    orig = rf._spawn
    rf._spawn = _leaky_spawn
    try:
        rc = rf.self_test()
    finally:
        rf._spawn = orig
    assert rc == 1, f"canary must fail when _spawn leaks the env (got rc={rc})"


def test_self_test_passes_with_scrub_intact():
    """Unchanged _spawn => all three boundaries hold (rc=0)."""
    assert rf.self_test() == 0
