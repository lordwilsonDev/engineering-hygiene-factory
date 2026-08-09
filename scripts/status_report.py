#!/usr/bin/env python3
"""status_report.py — derive constellation status FROM EVIDENCE.

The meta-move that kills claim-drift at the source: nothing in this file
asserts a project is "verified" — every status is DERIVED from the evidence
artifacts each project's own gate produced (factory_gate.json +
hygiene_aggregate.json under <project>/artifacts/hygiene/), cross-checked
against how fresh that evidence is relative to the project's last git
commit.

Status derivation (the only truth table):

    gate artifact missing           -> UNVERIFIED  (no evidence at all)
    gate verdict != PASS            -> FAILING     (gate ran and failed)
    hygiene verdict == fail         -> FAILING     (weakest leg failed)
    evidence older than last commit -> STALE       (code moved past the proof)
    evidence older than window      -> STALE       (nobody's run the gate lately)
    otherwise                       -> VERIFIED    (green AND current)

`--check` exits 1 if any project whose artifacts are PRESENT is FAILING (or
the generator itself errors) — the CI canary. Absent projects are reported
UNVERIFIED, not fatal (CI runners only have some repos checked out).

Outputs: <factory>/STATUS.md (human) + <factory>/artifacts/status/status.json
(machine). Optional `--with-ci` appends the last GitHub Actions factory-gate
conclusion per project via `gh` (best-effort; never fails the run).

Stdlib-only. Zero-spend: reads artifacts, runs `git`/`gh` read-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STALE_DAYS = 7

# The constellation: name -> {repo path, GitHub slug (for --with-ci)}.
# Evidence lives in <repo>/artifacts/hygiene/.
PROJECTS: list[dict[str, str]] = [
    {"name": "msb-v3", "repo": str(Path.home() / "msb-v3"), "slug": "lordwilsonDev/msb-v3"},
    {"name": "agent-reach", "repo": str(Path.home() / "agent-reach"), "slug": "lordwilsonDev/agent-reach"},
    {"name": "sovereign-mcp-os", "repo": str(Path.home() / "sovereign-mcp-os"), "slug": "lordwilsonDev/sovereign-mcp-os"},
    {"name": "sovereign-outcome-engine", "repo": str(Path.home() / "sovereign-outcome-engine"), "slug": "lordwilsonDev/sovereign-outcome-engine"},
    {"name": "nexus", "repo": str(Path.home() / "nexus"), "slug": "lordwilsonDev/nexus"},
    {"name": "domain-router", "repo": str(Path.home() / ".hermes" / "domain-router"), "slug": "lordwilsonDev/domain-router"},
    {"name": "skill-orchestration-os", "repo": str(Path.home() / ".hermes" / "skills" / "skill-orchestration-os"), "slug": "lordwilsonDev/skill-orchestration-os"},
]

# Status ordering for the aggregate verdict: worse wins.
_STATUS_WEIGHT = {"FAILING": 0, "UNVERIFIED": 1, "STALE": 2, "VERIFIED": 3}


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_json(path: Path) -> dict | None:
    """Read a JSON artifact; None if missing, {} if malformed (recorded)."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def last_commit_time(repo: Path) -> float | None:
    """Epoch seconds of the repo's last commit; None if not a git repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return None


def ci_conclusion(slug: str) -> str | None:
    """Last factory-gate CI conclusion for a repo slug (best-effort)."""
    if not shutil.which("gh"):
        return None
    try:
        proc = subprocess.run(
            ["gh", "run", "list", "--repo", slug, "--workflow", "factory-gate",
             "--limit", "1", "--json", "conclusion"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if proc.returncode != 0:
            return None
        rows = json.loads(proc.stdout or "[]")
        return rows[0]["conclusion"] if rows else None
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError):
        return None


def artifact_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def gate_verdict(gate: dict | None) -> str | None:
    """factory_gate.json verdict: RELEASE_VERDICT.release_verdict ("PASS")."""
    if not gate:
        return None
    rv = gate.get("RELEASE_VERDICT") or {}
    return rv.get("release_verdict") if isinstance(rv, dict) else None


def gate_pytest(gate: dict | None) -> tuple[bool | None, str | None]:
    """(pytest passed?, summary) from VERIFICATION.pytest."""
    if not gate:
        return None, None
    ver = gate.get("VERIFICATION") or {}
    pytest = ver.get("pytest") or {}
    if not isinstance(pytest, dict):
        return None, None
    return pytest.get("passed"), pytest.get("summary")


def gate_unknowns(gate: dict | None) -> int | None:
    if not gate:
        return None
    rv = gate.get("RELEASE_VERDICT") or {}
    unknowns = rv.get("unresolved_unknowns") if isinstance(rv, dict) else None
    return len(unknowns) if isinstance(unknowns, list) else None


def derive_state(gate: dict | None, aggregate: dict | None,
                 commit_ts: float | None, gate_mtime: float,
                 stale_seconds: int) -> tuple[str, list[str]]:
    """Truth table above. Returns (state, reasons)."""
    reasons: list[str] = []
    if gate is None:
        return "UNVERIFIED", ["no factory_gate.json artifact"]
    if gate_verdict(gate) != "PASS":
        return "FAILING", [f"gate verdict = {gate_verdict(gate)!r}"]
    agg_verdict = (aggregate or {}).get("factory_verdict")
    if agg_verdict == "fail":
        return "FAILING", ["hygiene aggregate verdict = fail"]
    if commit_ts is not None and gate_mtime and gate_mtime < commit_ts:
        return "STALE", ["gate artifact predates last commit"]
    age = now_utc().timestamp() - gate_mtime
    if gate_mtime and age > stale_seconds:
        return "STALE", [f"gate artifact {int(age // 86400)} days old (> {stale_seconds // 86400})"]
    reasons.append(f"gate PASS, artifact age {int(max(age, 0) // 3600)}h")
    return "VERIFIED", reasons


def build_status(with_ci: bool = False, stale_seconds: int = DEFAULT_STALE_DAYS * 86400) -> dict:
    projects: list[dict] = []
    for cfg in PROJECTS:
        repo = Path(cfg["repo"])
        evidence = repo / "artifacts" / "hygiene"
        gate_path = evidence / "factory_gate.json"
        agg_path = evidence / "hygiene_aggregate.json"
        gate = read_json(gate_path)
        aggregate = read_json(agg_path)
        commit_ts = last_commit_time(repo)
        state, reasons = derive_state(
            gate, aggregate, commit_ts, artifact_mtime(gate_path), stale_seconds)

        pytest_passed, pytest_summary = gate_pytest(gate)
        entry: dict = {
            "project": cfg["name"],
            "repo": str(repo),
            "state": state,
            "gate": gate_verdict(gate),
            "hygiene": (aggregate or {}).get("factory_verdict"),
            "pytest_passed": pytest_passed,
            "pytest_summary": pytest_summary,
            "unresolved_unknowns": gate_unknowns(gate),
            "evidence_age_h": None if not gate_path.exists()
                else round(max(now_utc().timestamp() - artifact_mtime(gate_path), 0) / 3600, 1),
            "stale_after_last_commit": bool(commit_ts and gate_path.exists()
                and artifact_mtime(gate_path) < commit_ts),
            "reasons": reasons,
        }
        if with_ci:
            entry["ci"] = ci_conclusion(cfg["slug"])
        projects.append(entry)

    # Aggregate: worst state wins (fails loudly over stale, etc.).
    states = sorted({p["state"] for p in projects}, key=lambda s: _STATUS_WEIGHT[s])
    return {
        "generated_at": now_utc().isoformat(),
        "generator": "scripts/status_report.py",
        "stale_after_days": stale_seconds // 86400,
        "verdict": states[0] if states else "UNVERIFIED",
        "projects": projects,
    }


def render_markdown(status: dict) -> str:
    lines = [
        "# Constellation Status (derived from evidence)",
        "",
        f"Generated: `{status['generated_at']}` by `{status['generator']}`",
        "",
        "**Nothing here is asserted — every state is derived from each "
        "project's `artifacts/hygiene/` gate artifacts and freshness vs its "
        "last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE.",
        "",
        f"Aggregate verdict: **{status['verdict']}**",
        "",
        "| Project | State | Gate | Hygiene | pytest | Evidence age | CI (last run) |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in status["projects"]:
        lines.append(
            f"| {p['project']} | **{p['state']}** | {p['gate'] or '-'} | "
            f"{p['hygiene'] or '-'} | {p['pytest_passed'] if p['pytest_passed'] is not None else '-'} | "
            f"{p['evidence_age_h']}h | {p.get('ci') or '-'} |"
        )
    lines.append("")
    lines.append("## pytest summaries")
    for p in status["projects"]:
        if p.get("pytest_summary"):
            unknowns = p.get("unresolved_unknowns")
            suffix = f" ({unknowns} unresolved unknowns)" if unknowns else ""
            lines.append(f"- `{p['project']}`: {p['pytest_summary']}{suffix}")
    lines.append("")
    lines.append("## Why")
    for p in status["projects"]:
        for r in p["reasons"]:
            lines.append(f"- `{p['project']}`: {r}")
    lines.append("")
    lines.append("_Regenerate with: `python scripts/status_report.py` "
                 "(add `--with-ci` for GitHub run conclusions). `--check` "
                 "exits 1 if any present project is FAILING._")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive constellation status from evidence")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any present project is FAILING or the generator errors")
    parser.add_argument("--with-ci", action="store_true",
                        help="append last GitHub factory-gate conclusion per project (needs gh)")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS,
                        help="evidence older than this is STALE (default 7)")
    args = parser.parse_args(argv)

    try:
        status = build_status(with_ci=args.with_ci,
                              stale_seconds=args.stale_days * 86400)
    except Exception as exc:  # noqa: BLE001
        print(f"status generator failed: {type(exc).__name__}: {exc}")
        return 1

    out_dir = ROOT / "artifacts" / "status"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (ROOT / "STATUS.md").write_text(render_markdown(status), encoding="utf-8")
    print(f"status.json -> {out_dir / 'status.json'}")
    print(f"STATUS.md   -> {ROOT / 'STATUS.md'}")
    for p in status["projects"]:
        print(f"  {p['project']:28s} {p['state']:10s} gate={p['gate'] or '-':4s} "
              f"hygiene={p['hygiene'] or '-':8s} age={p['evidence_age_h']}h")

    if args.check:
        failing = [p["project"] for p in status["projects"]
                   if p["state"] == "FAILING"]
        if failing:
            print(f"check FAILED: present projects in FAILING state: {failing}")
            return 1
        print("check PASSED: no present project is FAILING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
