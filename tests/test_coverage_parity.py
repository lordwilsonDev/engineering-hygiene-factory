#!/usr/bin/env python3
"""Coverage floor parity guard.

Ensures that each project's scripts/hygiene/suite.json coverage_floor matches
the --cov-fail-under argument specified in its CI workflow (.github/workflows/).
If suite.json and CI drift, this test fails loudly.
"""

import json
import re
from pathlib import Path
import pytest

PROJECT_PATHS = {
    "msb-v3": Path.home() / "msb-v3",
    "agent-reach": Path.home() / "agent-reach",
    "sovereign-mcp-os": Path.home() / "sovereign-mcp-os",
    "sovereign-outcome-engine": Path.home() / "sovereign-outcome-engine",
    "nexus": Path.home() / "nexus",
}


def _get_suite_floor(repo_root: Path) -> int:
    suite_json = repo_root / "scripts" / "hygiene" / "suite.json"
    if not suite_json.exists():
        pytest.skip(f"suite.json not found at {suite_json}")
    data = json.loads(suite_json.read_text(encoding="utf-8"))
    floor = float(data.get("coverage_floor", 0.0))
    return int(round(floor * 100))


def _get_ci_floor(repo_root: Path) -> int | None:
    """The coverage gate lives in the factory-gate workflow.

    Only scan .github/workflows/factory-gate.yml (the workflow that runs the
    coverage gate), and only match RUN lines (indented under a `run:` block),
    never comments. Repos may carry other workflows (e.g. ci.yml) whose own
    fail-under must not be compared against the suite floor.
    """
    gate_yml = repo_root / ".github" / "workflows" / "factory-gate.yml"
    if not gate_yml.exists():
        return None
    for line in gate_yml.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # pytest-cov uses --cov-fail-under; the coverage CLI uses --fail-under
        # (SOE's subprocess-coverage gate). Both express the floor as a percent.
        match = re.search(r"--(?:cov-)?fail-under=(\d+)", stripped)
        if match:
            return int(match.group(1))
    return None


@pytest.mark.parametrize("project_name", list(PROJECT_PATHS.keys()))
def test_coverage_floor_parity(project_name: str) -> None:
    repo_root = PROJECT_PATHS[project_name]
    if not repo_root.exists():
        pytest.skip(f"Project directory not found at {repo_root}")

    suite_floor = _get_suite_floor(repo_root)
    ci_floor = _get_ci_floor(repo_root)

    if ci_floor is None:
        pytest.skip(f"No --cov-fail-under found in {project_name} CI workflows")

    assert suite_floor == ci_floor, (
        f"Coverage floor mismatch in {project_name}!\n"
        f"  suite.json: {suite_floor}%\n"
        f"  CI workflow: {ci_floor}%\n"
        "Keep suite.json and CI --cov-fail-under in sync!"
    )
