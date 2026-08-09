#!/usr/bin/env python3
"""d03 scrub-list sync guard.

`run_factory.py`'s ZERO_SPEND_ENV_VARS is the canonical paid-credential scrub
list; the domain-router d03 runner carries a copy (kept in lockstep by an
explicit comment). If one list changes and the other doesn't, a gate that
claims zero-spend could leak through the stale list. This test reads BOTH
lists and asserts they match, so drift fails loudly instead of silently.

The d03 file lives in the sibling domain-router tree, not this repo. When it
is absent — e.g. this repo is checked out alone in CI without the optional
domain-router checkout — the test SKIPS with an explicit reason rather than
hard-failing on a missing sibling. Set D03_RUNNER_PATH to point at the d03
runner to enforce the check in any environment.
"""

import ast
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_factory as rf  # noqa: E402

_D03_DEFAULT = (
    Path.home() / ".hermes" / "domain-router" / "scripts" / "hygiene"
    / "d03_orchestration_smoke_runner.py"
)
D03_RUNNER = Path(os.environ.get("D03_RUNNER_PATH", _D03_DEFAULT))


def _tuple_literals(source: str, name: str = "ZERO_SPEND_ENV_VARS") -> list[str]:
    """Return the string literals of the first <name> = (...) assignment."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value if isinstance(node, ast.Assign) else node.annotation
            for target in targets:
                if (
                    isinstance(target, ast.Name) and target.id == name
                    and isinstance(value, ast.Tuple)
                ):
                    return [
                        elt.value for elt in value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
    return []


def test_zero_spend_lists_match_d03() -> None:
    if not D03_RUNNER.exists():
        pytest.skip(
            f"d03 runner not present ({D03_RUNNER}); set D03_RUNNER_PATH "
            "to enforce the scrub-list sync"
        )
    d03_names = _tuple_literals(D03_RUNNER.read_text(encoding="utf-8"))
    assert d03_names, f"could not parse ZERO_SPEND_ENV_VARS from {D03_RUNNER}"
    factory_names = list(rf.ZERO_SPEND_ENV_VARS)
    assert d03_names == factory_names, (
        "ZERO_SPEND_ENV_VARS DRIFT between factory and d03 runner!\n"
        f"  factory ({len(factory_names)}): {factory_names}\n"
        f"  d03     ({len(d03_names)}): {d03_names}\n"
        "Keep both lists in lockstep (see the comment in "
        "d03_orchestration_smoke_runner.py)."
    )
