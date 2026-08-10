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
    recorded git_head != current code HEAD -> STALE (code moved past the proof;
                                                      works from fresh CI checkouts)
    evidence older than last NON-EVIDENCE commit -> STALE  (code moved past the proof)
    evidence older than window      -> STALE       (nobody's run the gate lately)
    otherwise                       -> VERIFIED    (green AND current)

`--check` exits 1 if any project whose artifacts are PRESENT is FAILING (or
the generator itself errors) — the CI canary. Absent projects are reported
UNVERIFIED, not fatal (CI runners only have some repos checked out).
`--strict` exits 1 on ANY state below VERIFIED (FAILING, UNVERIFIED,
STALE) — use it where all evaluated repos exist and "not red" must mean
"green and current". `--only a,b` scopes evaluation to named projects (and
therefore which projects --strict can fail on) — CI uses it to gate exactly
the repos it checked out. Repos resolve under MSB_STATUS_HOME (default ~),
so CI can point the constellation at its checkout workspace.

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
    {"name": "msb-v3", "repo": "msb-v3", "slug": "lordwilsonDev/msb-v3"},
    {"name": "agent-reach", "repo": "agent-reach", "slug": "lordwilsonDev/agent-reach"},
    {"name": "sovereign-mcp-os", "repo": "sovereign-mcp-os", "slug": "lordwilsonDev/sovereign-mcp-os"},
    {"name": "sovereign-outcome-engine", "repo": "sovereign-outcome-engine", "slug": "lordwilsonDev/sovereign-outcome-engine"},
    {"name": "nexus", "repo": "nexus", "slug": "lordwilsonDev/nexus"},
    {"name": "domain-router", "repo": str(Path.home() / ".hermes" / "domain-router"), "slug": "lordwilsonDev/domain-router"},
    {"name": "skill-orchestration-os", "repo": str(Path.home() / ".hermes" / "skills" / "skill-orchestration-os"), "slug": "lordwilsonDev/skill-orchestration-os"},
]

def repo_root() -> Path:
    """Base directory for bare-name project repos (MSB_STATUS_HOME).

    Empty/whitespace values are treated as unset (falls back to ~) so a
    stale or mis-set env var can never silently rebase repos onto the
    current working directory.
    """
    value = os.environ.get("MSB_STATUS_HOME", "").strip()
    return Path(value) if value else Path.home()


def repo_path(name: str) -> Path:
    """Resolve a project's repo directory.

    Absolute paths in PROJECTS (and test overrides) win as-is; bare relative
    names (the constellation repos checked out by CI) resolve under
    MSB_STATUS_HOME so the factory's own self-test can gate the whole
    constellation from fresh checkouts.
    """
    for cfg in PROJECTS:
        if cfg["name"] == name:
            repo = cfg.get("repo", name)
            p = Path(repo)
            return p if p.is_absolute() else repo_root() / p
    return repo_root() / name

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


def last_commit_time(repo: Path,
                     evidence_rel: str = "artifacts/hygiene") -> float | None:
    """Epoch seconds of the repo's last NON-EVIDENCE commit; None if not a git
    repo or every commit touches only evidence.

    The evidence directory is excluded (via the `:(exclude)` magic pathspec,
    git >= 2.13) so committing gate artifacts never makes the evidence itself
    look stale — committing proof must not invalidate it. STALE means "code
    moved past the proof", not "proof was versioned". The age-window check
    uses the artifact mtime directly, so a repo with no code commits needs no
    fallback here: no code commit -> no "code moved past the proof" signal.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%ct", "--",
             f":(exclude){evidence_rel}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return None


def code_head(repo: Path,
              evidence_rel: str = "artifacts/hygiene") -> str | None:
    """Full hash of the repo's last NON-EVIDENCE commit; None if not git.

    Mirrors last_commit_time's pathspec. This is the hash-based freshness
    check that WORKS from a fresh CI checkout: factory_gate.json records
    VERIFICATION.git_head (the commit the gate ran against), and status
    compares it to code_head(repo) — a mismatch means code moved past the
    proof even when file mtimes are all checkout-time.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%H", "--",
             f":(exclude){evidence_rel}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def recorded_head(gate: dict | None) -> str | None:
    """VERIFICATION.git_head from the gate artifact (the commit it ran on)."""
    if not gate:
        return None
    ver = gate.get("VERIFICATION") or {}
    head = ver.get("git_head") if isinstance(ver, dict) else None
    return head if isinstance(head, str) and head else None


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


def mutation_score(repo: Path) -> float | None:
    """Mutation score % from <repo>/artifacts/hygiene/mutation_score.json.

    Produced by the project's own mutation_score_snapshot.py (zero-spend
    read of mutmut's verdict files). None when the project has no mutation
    evidence at all.
    """
    snap = read_json(repo / "artifacts" / "hygiene" / "mutation_score.json")
    score = snap.get("score_pct") if snap else None
    return score if isinstance(score, (int, float)) else None


def gate_coverage(gate: dict | None) -> tuple[float | None, float | None]:
    """(measured_pct, floor_pct) from the gate's VERIFICATION.coverage block.

    The coverage-floor gate is derived evidence like everything else: the
    percentage the project's last in-factory pytest --cov run measured, and
    the floor it declared. None when the project has no coverage config.
    """
    if not gate:
        return None, None
    ver = gate.get("VERIFICATION") or {}
    cov = ver.get("coverage") or {}
    if not isinstance(cov, dict) or not cov.get("configured"):
        return None, None
    pct = cov.get("pct")
    floor = cov.get("floor_pct")
    return (float(pct) if isinstance(pct, (int, float)) else None,
            float(floor) if isinstance(floor, (int, float)) else None)


def derive_state(gate: dict | None, aggregate: dict | None,
                 commit_ts: float | None, gate_mtime: float,
                 stale_seconds: int, head_now: str | None = None,
                 head_recorded: str | None = None) -> tuple[str, list[str]]:
    """Truth table above. Returns (state, reasons).

    `head_now`/`head_recorded` are the repo's current code HEAD hash and the
    hash the gate recorded (VERIFICATION.git_head). When both exist and
    differ, the code moved past the proof even if mtimes look fresh — the
    hash check is what makes staleness detectable from a fresh CI checkout.
    """
    reasons: list[str] = []
    if gate is None:
        return "UNVERIFIED", ["no factory_gate.json artifact"]
    if gate_verdict(gate) != "PASS":
        return "FAILING", [f"gate verdict = {gate_verdict(gate)!r}"]
    agg_verdict = (aggregate or {}).get("factory_verdict")
    if agg_verdict == "fail":
        return "FAILING", ["hygiene aggregate verdict = fail"]
    if head_now and head_recorded and head_now != head_recorded:
        return "STALE", [f"gate recorded commit {head_recorded[:8]}, "
                         f"code HEAD is {head_now[:8]} (code moved past the proof)"]
    if commit_ts is not None and gate_mtime and gate_mtime < commit_ts:
        return "STALE", ["gate artifact predates last commit"]
    age = now_utc().timestamp() - gate_mtime
    if gate_mtime and age > stale_seconds:
        return "STALE", [f"gate artifact {int(age // 86400)} days old (> {stale_seconds // 86400})"]
    reasons.append(f"gate PASS, artifact age {int(max(age, 0) // 3600)}h")
    return "VERIFIED", reasons


def build_status(with_ci: bool = False, stale_seconds: int = DEFAULT_STALE_DAYS * 86400,
                 only: list[str] | None = None) -> dict:
    """Derive every project's state from its own evidence artifacts.

    `only` scopes the evaluation to a subset of PROJECTS (by name) — used by
    CI to gate exactly the repos it has checked out, so absent evidence in
    repos covered by their own workflows (skill-orchestration-os has no
    factory gate by design; domain-router's evidence lives outside the
    checkout) can never turn the strict gate permanently red.
    """
    names = set(only) if only else None
    projects: list[dict] = []
    for cfg in PROJECTS:
        if names is not None and cfg["name"] not in names:
            continue
        repo = repo_path(cfg["name"])
        evidence = repo / "artifacts" / "hygiene"
        gate_path = evidence / "factory_gate.json"
        agg_path = evidence / "hygiene_aggregate.json"
        gate = read_json(gate_path)
        aggregate = read_json(agg_path)
        commit_ts = last_commit_time(repo)
        state, reasons = derive_state(
            gate, aggregate, commit_ts, artifact_mtime(gate_path), stale_seconds,
            head_now=code_head(repo), head_recorded=recorded_head(gate))

        pytest_passed, pytest_summary = gate_pytest(gate)
        coverage_pct, coverage_floor = gate_coverage(gate)
        entry: dict = {
            "project": cfg["name"],
            "repo": str(repo),
            "state": state,
            "gate": gate_verdict(gate),
            "hygiene": (aggregate or {}).get("factory_verdict"),
            "mutation_score_pct": mutation_score(repo),
            "coverage_pct": coverage_pct,
            "coverage_floor_pct": coverage_floor,
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
        "| Project | State | Gate | Hygiene | Mutation | Cov | pytest | Evidence age | CI (last run) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in status["projects"]:
        mutation = p.get("mutation_score_pct")
        mutation_cell = f"{mutation}%" if mutation is not None else "-"
        cov = p.get("coverage_pct")
        cov_floor = p.get("coverage_floor_pct")
        if cov is None:
            cov_cell = "-"  # no coverage evidence at all (even with a declared floor)
        elif cov_floor is None:
            cov_cell = f"{cov}%"
        else:
            cov_cell = f"{cov}%/{cov_floor:.0f}%"
        lines.append(
            f"| {p['project']} | **{p['state']}** | {p['gate'] or '-'} | "
            f"{p['hygiene'] or '-'} | {mutation_cell} | {cov_cell} | "
            f"{p['pytest_passed'] if p['pytest_passed'] is not None else '-'} | "
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
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if ANY project is below VERIFIED (FAILING/UNVERIFIED/STALE)")
    parser.add_argument("--with-ci", action="store_true",
                        help="append last GitHub factory-gate conclusion per project (needs gh)")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS,
                        help="evidence older than this is STALE (default 7)")
    parser.add_argument("--only", type=str, default=None,
                        help="comma-separated project names to evaluate (CI scoping); "
                             "default: all projects")
    args = parser.parse_args(argv)

    only = [n.strip() for n in args.only.split(",") if n.strip()] if args.only else None
    if only:
        known = {cfg["name"] for cfg in PROJECTS}
        unknown = [n for n in only if n not in known]
        if unknown:
            print(f"WARN: --only names not in PROJECTS (ignored): {unknown}",
                  file=sys.stderr)
    try:
        status = build_status(with_ci=args.with_ci,
                              stale_seconds=args.stale_days * 86400,
                              only=only)
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
        failing = [p["project"] for p in status["projects"] if p["state"] == "FAILING"]
        if failing:
            print(f"check FAILED: present projects in FAILING state: {failing}")
            return 1
        print("check PASSED: no present project is FAILING")
    if args.strict:
        below = [p["project"] for p in status["projects"]
                 if _STATUS_WEIGHT[p["state"]] < _STATUS_WEIGHT["VERIFIED"]]
        if below:
            print(f"strict FAILED: projects below VERIFIED (FAILING/UNVERIFIED/STALE): {below}")
            return 1
        print("strict PASSED: every project is VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
