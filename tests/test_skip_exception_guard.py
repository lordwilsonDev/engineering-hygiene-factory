#!/usr/bin/env python3
"""Runner skip-exception guard.

The `_Skip` hazard (found and fixed in skill-os smoke_test.py, 2026-08-10):
a script that pytest collects AND defines a custom exception subclassing a
PLAIN exception (Exception, ValueError, ...) AND catches that class itself
(control-flow: the standalone runner prints a visible SKIP) is a trap —
pytest treats the raise as a hard failure. With -x the first one aborts the
whole run; under mutmut every mutant verdict is poisoned. The bug only
surfaces in environments where the skip condition fires (e.g. CI without
sibling trees), which is why it sailed through local runs.

The correct dual-mode pattern (what smoke_test.py now uses):

    try:
        import pytest
        _SKIP_EXC = pytest.skip.Exception   # pytest: a real skip
    except ImportError:
        _SKIP_EXC = Exception               # standalone: caught by the runner
    class _Skip(_SKIP_EXC): ...

This guard makes the bug class machine-checked instead of hand-audited: it
scans the constellation's runner trees and flags every custom exception that
satisfies ALL THREE conditions:

  1. the file is pytest-collectible (name matches test_*.py / *_test.py, or
     it lives under a tests/ dir),
  2. it defines a class whose base is a plain exception-family name — a
     single identifier of Exception / BaseException / *Error (dotted bases
     like pytest.skip.Exception and dual-mode variable bases like
     _SKIP_EXC never match),
  3. the same file catches that class (proving control-flow use rather than
     a domain error that SHOULD fail under pytest).

Dependencies: stdlib only (ast, pathlib). Mutmut-friendly: the fixture
hazard sources are plain string literals, so scanning this test file itself
finds nothing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# The constellation's runner trees, resolved the same way status_report.py
# and test_coverage_parity.py resolve them (skip visibly when absent — CI
# checkouts only carry some repos).
PROJECT_ROOTS: dict[str, Path] = {
    "msb-v3": Path.home() / "msb-v3",
    "agent-reach": Path.home() / "agent-reach",
    "sovereign-mcp-os": Path.home() / "sovereign-mcp-os",
    "sovereign-outcome-engine": Path.home() / "sovereign-outcome-engine",
    "nexus": Path.home() / "nexus",
    "domain-router": Path.home() / ".hermes" / "domain-router",
    "skill-orchestration-os": Path.home() / ".hermes" / "skills" / "skill-orchestration-os",
}

# Paths inside a project that can contain runner scripts (never the whole
# repo: library modules under src/ runtime/ are not standalone runners).
SCAN_DIRS = ("scripts", "tests")

_PLAIN_EXCEPTION_NAMES = {"Exception", "BaseException"}


def _is_plain_exception_name(name: str) -> bool:
    """True for Exception-family bases that pytest does NOT special-case.

    pytest.skip.Exception is dotted (never an ast.Name), so it can't reach
    here. A bare identifier ending in Error (ValueError, RuntimeError, a
    custom *Error) or Exception/BaseException is a plain exception: raising
    it under pytest is a hard failure.
    """
    return name in _PLAIN_EXCEPTION_NAMES or name.endswith("Error")


def _find_caught_custom_exceptions(source: str) -> list[tuple[str, int]]:
    """[(class_name, lineno)] for the skip-exception hazard in `source`.

    A class is flagged only when it is (a) defined here with a plain-exception
    base, (b) actually raised somewhere in this file (dead classes are not
    control flow), and (c) caught here either by name or by a broad
    `except Exception` / `except BaseException` / bare `except:` — the way a
    standalone runner implements skip semantics. All three are required so a
    domain error that should fail under pytest is never flagged.
    """
    tree = ast.parse(source)
    plain_classes: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.bases:
            base = node.bases[0]
            if isinstance(base, ast.Name) and _is_plain_exception_name(base.id):
                plain_classes[node.name] = node.lineno
    if not plain_classes:
        return []
    raised: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc
            func = exc.func if isinstance(exc, ast.Call) else exc
            if isinstance(func, ast.Name) and func.id in plain_classes:
                raised.add(func.id)
    if not raised:
        return []
    caught: set[str] = set()
    broad_catch = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None or (
                isinstance(node.type, ast.Name)
                and node.type.id in ("Exception", "BaseException")
            ):
                broad_catch = True
                continue
            types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            for t in types:
                if isinstance(t, ast.Name) and t.id in plain_classes:
                    caught.add(t.id)
    flagged = (name for name in raised if name in caught or broad_catch)
    return [(name, plain_classes[name]) for name in sorted(flagged)]


def _pytest_collectible(path: Path) -> bool:
    """Static check: pytest's default python_files are test_*.py / *_test.py
    (plus anything under a tests/ dir)."""
    return (
        path.name.startswith("test_")
        or path.name.endswith("_test.py")
        or "tests" in path.parts
    )


def _project_scan_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        d = repo / d
        if d.is_dir():
            files.extend(sorted(d.rglob("*.py")))
    # Root-level test files (e.g. domain-router/test_router.py).
    files.extend(sorted(repo.glob("test_*.py")))
    files.extend(sorted(repo.glob("*_test.py")))
    return files


def _factory_scan_files(factory: Path) -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        d = factory / d
        if d.is_dir():
            files.extend(sorted(d.rglob("*.py")))
    files.extend(sorted(factory.glob("*.py")))
    return files


def _scan(files: list[Path]) -> list[tuple[str, str, int]]:
    """[(path, class_name, lineno)] violations across the given files.

    Non-collectible files are skipped before reading/parsing: a syntax error
    in a helper module is not this guard's business (a broken runner that
    pytest collects is)."""
    violations: list[tuple[str, str, int]] = []
    for path in files:
        if not _pytest_collectible(path):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            found = _find_caught_custom_exceptions(source)
        except SyntaxError as exc:  # a broken collectible runner is a finding
            violations.append((str(path), f"<unparseable: {exc}>", 0))
            continue
        for name, lineno in found:
            violations.append((str(path), name, lineno))
    return violations


def _fmt(violations: list[tuple[str, str, int]], label: str) -> str:
    lines = [f"skip-exception hazard in {label} ({len(violations)}):"]
    for path, name, lineno in violations:
        lines.append(
            f"  {path}:{lineno}: class {name} subclasses a plain exception, is "
            "caught by the file's own runner, and lives in a pytest-collectible "
            "file — under pytest (-x / mutmut) the raise is a hard failure, not "
            "a skip. Use the dual-mode pattern: "
            "class X(pytest.skip.Exception if pytest else Exception)."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scanner unit tests (the guard is only as honest as its detector).
# ---------------------------------------------------------------------------

def test_flags_plain_exception_caught_in_collectible_file() -> None:
    src = (
        "class _Skip(Exception):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise _Skip('env gap')\n"
        "def main():\n"
        "    try:\n"
        "        test_x()\n"
        "    except _Skip as e:\n"
        "        print('SKIP', e)\n"
    )
    assert _find_caught_custom_exceptions(src) == [("_Skip", 1)]


def test_flags_custom_error_base() -> None:
    src = (
        "class SkipSignal(ValueError):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise SkipSignal()\n"
        "try:\n"
        "    test_x()\n"
        "except SkipSignal:\n"
        "    pass\n"
    )
    assert _find_caught_custom_exceptions(src) == [("SkipSignal", 1)]


def test_allows_dual_mode_pattern() -> None:
    """The fixed smoke_test.py shape: variable base, not a plain exception."""
    src = (
        "try:\n"
        "    import pytest\n"
        "    _PYTEST_SKIP_EXC = pytest.skip.Exception\n"
        "except ImportError:\n"
        "    _PYTEST_SKIP_EXC = Exception\n"
        "class _Skip(_PYTEST_SKIP_EXC):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise _Skip('env gap')\n"
        "try:\n"
        "    test_x()\n"
        "except _Skip as e:\n"
        "    print('SKIP', e)\n"
    )
    assert _find_caught_custom_exceptions(src) == []


def test_allows_pytest_dotted_base() -> None:
    src = (
        "class _Skip(pytest.skip.Exception):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise _Skip()\n"
        "try:\n"
        "    test_x()\n"
        "except _Skip:\n"
        "    pass\n"
    )
    assert _find_caught_custom_exceptions(src) == []


def test_allows_uncaught_domain_error() -> None:
    """A genuine domain exception that propagates must keep failing under
    pytest — the guard must not flag it."""
    src = (
        "class TransitionRejection(Exception):\n"
        "    pass\n"
        "def transition():\n"
        "    raise TransitionRejection('prohibited')\n"
    )
    assert _find_caught_custom_exceptions(src) == []


def test_allows_hazard_in_non_collectible_file(tmp_path: Path) -> None:
    """A standalone CLI runner that pytest never collects is not the hazard."""
    runner = tmp_path / "d01_runner.py"
    runner.write_text(
        "class _Skip(Exception):\n    pass\n"
        "try:\n    raise _Skip()\nexcept _Skip:\n    pass\n",
        encoding="utf-8",
    )
    assert _scan([runner]) == []


def test_flags_broad_exception_catch() -> None:
    """Skip semantics implemented with a broad `except Exception:` (not the
    custom name) is still the hazard — the blind spot the by-name check alone
    would miss."""
    src = (
        "class _Skip(Exception):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise _Skip('env gap')\n"
        "try:\n"
        "    test_x()\n"
        "except Exception as e:\n"
        "    print('SKIP', e)\n"
    )
    assert _find_caught_custom_exceptions(src) == [("_Skip", 1)]


def test_flags_bare_except_catch() -> None:
    src = (
        "class _Skip(Exception):\n"
        "    pass\n"
        "def test_x():\n"
        "    raise _Skip()\n"
        "try:\n"
        "    test_x()\n"
        "except:\n"
        "    pass\n"
    )
    assert _find_caught_custom_exceptions(src) == [("_Skip", 1)]


def test_allows_caught_but_never_raised_class() -> None:
    """Dead code (a caught class that is never raised) is not control flow."""
    src = (
        "class _Skip(Exception):\n"
        "    pass\n"
        "def test_x():\n"
        "    pass\n"
        "try:\n"
        "    test_x()\n"
        "except _Skip as e:\n"
        "    print('SKIP', e)\n"
    )
    assert _find_caught_custom_exceptions(src) == []


# ---------------------------------------------------------------------------
# The enforcement: scan the constellation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_name", list(PROJECT_ROOTS))
def test_no_plain_skip_exception_in_project(project_name: str) -> None:
    repo = PROJECT_ROOTS[project_name]
    if not repo.exists():
        pytest.skip(f"project not present at {repo}")
    violations = _scan(_project_scan_files(repo))
    assert not violations, _fmt(violations, project_name)


def test_no_plain_skip_exception_in_factory() -> None:
    factory = Path(__file__).resolve().parents[1]
    violations = _scan(_factory_scan_files(factory))
    assert not violations, _fmt(violations, "engineering-hygiene-factory")
