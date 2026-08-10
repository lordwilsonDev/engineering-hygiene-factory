#!/usr/bin/env python3
"""d03/d05/d07 scrub-list sync guard.

`run_factory.py`'s ZERO_SPEND_ENV_VARS is the canonical paid-credential scrub
list; the domain-router d03, d05 AND d07 runners each carry a copy (kept in
lockstep by an explicit comment). If one list changes and the others don't, a
gate that claims zero-spend could leak through the stale list. This test
reads ALL lists and asserts they match, so drift fails loudly instead of
silently.

The d03/d05/d07 files live in the sibling domain-router tree, not this repo.
When they are absent — e.g. this repo is checked out alone in CI without the
optional domain-router checkout — the test SKIPS with an explicit reason
rather than hard-failing on a missing sibling. Set D03_RUNNER_PATH /
D05_RUNNER_PATH / D07_RUNNER_PATH to point at the runners to enforce the
check in any environment.
"""

import ast
import os
from pathlib import Path

import pytest

import run_factory as rf  # noqa: E402  (sys.path via root conftest.py)

_D03_DEFAULT = (
    Path.home() / ".hermes" / "domain-router" / "scripts" / "hygiene"
    / "d03_orchestration_smoke_runner.py"
)
D03_RUNNER = Path(os.environ.get("D03_RUNNER_PATH", _D03_DEFAULT))
_D05_DEFAULT = (
    Path.home() / ".hermes" / "domain-router" / "scripts" / "hygiene"
    / "d05_vault_freshness_runner.py"
)
D05_RUNNER = Path(os.environ.get("D05_RUNNER_PATH", _D05_DEFAULT))
_D07_DEFAULT = (
    Path.home() / ".hermes" / "domain-router" / "scripts" / "hygiene"
    / "d07_structural_classifier_runner.py"
)
D07_RUNNER = Path(os.environ.get("D07_RUNNER_PATH", _D07_DEFAULT))


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


def _assert_list_matches(runner: Path, label: str) -> None:
    names = _tuple_literals(runner.read_text(encoding="utf-8"))
    assert names, f"could not parse ZERO_SPEND_ENV_VARS from {runner}"
    factory_names = list(rf.ZERO_SPEND_ENV_VARS)
    assert names == factory_names, (
        "ZERO_SPEND_ENV_VARS DRIFT between factory and "
        f"{label} runner!\n"
        f"  factory ({len(factory_names)}): {factory_names}\n"
        f"  {label:<7} ({len(names)}): {names}\n"
        "Keep all lists in lockstep (see the comment in the runners)."
    )


def test_zero_spend_lists_match_d03() -> None:
    if not D03_RUNNER.exists():
        pytest.skip(
            f"d03 runner not present ({D03_RUNNER}); set D03_RUNNER_PATH "
            "to enforce the scrub-list sync"
        )
    _assert_list_matches(D03_RUNNER, "d03")


def test_zero_spend_lists_match_d05() -> None:
    if not D05_RUNNER.exists():
        pytest.skip(
            f"d05 runner not present ({D05_RUNNER}); set D05_RUNNER_PATH "
            "to enforce the scrub-list sync"
        )
    _assert_list_matches(D05_RUNNER, "d05")


def test_zero_spend_lists_match_d07() -> None:
    if not D07_RUNNER.exists():
        pytest.skip(
            f"d07 runner not present ({D07_RUNNER}); set D07_RUNNER_PATH "
            "to enforce the scrub-list sync"
        )
    _assert_list_matches(D07_RUNNER, "d07")
