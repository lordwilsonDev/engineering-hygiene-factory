#!/usr/bin/env python3
"""OQAL / BEHF factory orchestrator — executable control loop.

Implements the `factory-meta` contract: select member runners, run them,
collect evidence artifacts, validate them against the schemas, and gate the
final verdict by the *weakest* member verdict.

Aggregation rule (from skills/factory-meta/SKILL.md):
  any `fail`     -> factory FAIL
  any `unknown`  -> factory BLOCKED
  only `pass`    -> factory PASS
  `blocked` members are non-fatal but are recorded (they mean "not proven").

How it runs:
  - Default project is the msb-v3 repo (overridable via MSB_REPO env or
    --project). If the project has scripts/hygiene/hygiene_runner.py, this
    script invokes it (--all --json) and aggregates the real results.
  - If no hygiene suite exists, each member skill is recorded as `blocked`
    with a note (honest: not run, not proven) — never a silent pass.
  - Two cross-cutting gates get REAL evidence, not assumptions:
      regression_passed  <- runs `pytest tests/ -q` in the project
      live_auth_verified <- probes the live server's x-mcp-secret gate
                            (correct secret -> 200, wrong/missing -> 401)

Zero-spend by construction: every subprocess the factory spawns (pytest +
hygiene suite) runs with paid-API credentials scrubbed from its env
(ZERO_SPEND_ENV_VARS), so a leaked DEEPSEEK/ANTHROPIC/OPENAI/GEMINI/CLAUDE/
TAVILY/GROQ key can never turn the gate into a paid API call. Internal
secrets (MCP_BRIDGE_SECRET, OLLAMA_MODEL, ...) are preserved.

Output: <project>/artifacts/hygiene/factory_gate.json
Exit code: 0 when the gate is PASS or BLOCKED-with-no-fail; 1 on any FAIL.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request as urllib_request
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from schema_validate import validate_artifact_file

FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT = Path(os.environ.get("MSB_REPO", Path.home() / "msb-v3"))
PY = os.environ.get("MSB_PYTHON", "/opt/homebrew/Caskroom/miniforge/base/bin/python")

# Paid-API credential env vars that must NEVER reach a subprocess the gate
# spawns. The gate runs the project's real pytest suite and hygiene runners;
# if one of them ever wires a live paid call (e.g. msb-v3's latent
# TavilyResearchBackend), a leaked key would turn the gate into a spend. The
# live-auth probe is exempt by design: it runs in-process with urllib and
# needs only the internal MCP_BRIDGE_SECRET (kept).
ZERO_SPEND_ENV_VARS = (
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENERATIVE_AI_API_KEY",
    "TAVILY_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
)


def _zero_spend_env() -> tuple[dict[str, str], int]:
    """Copy the ambient env minus paid-API credentials.

    Returns (env, stripped_count). Internal secrets (MCP_BRIDGE_SECRET,
    MSB_RAG_API_KEY, OLLAMA_MODEL, ...) and PATH survive untouched.
    """
    env = os.environ.copy()
    stripped = 0
    for k in ZERO_SPEND_ENV_VARS:
        if k in env:
            del env[k]
            stripped += 1
    return env, stripped


_SELF_TEST_CHILD = (
    "import os, sys\n"
    "for n in sys.argv[1:]:\n"
    "    print('HAS' if n in os.environ else 'CLEAN', n)\n"
)

# The one internal secret the factory legitimately uses: the live-auth probe
# reads it from os.environ (in-process urllib) and the h02 server boot needs
# it in subprocess envs. It must NEVER be treated like a paid credential.
_INTERNAL_SECRET = "MCP_BRIDGE_SECRET"


def _spawn(args: list[str], project: Path | None = None,
           timeout: int = 900) -> subprocess.CompletedProcess:
    """Spawn a subprocess with the zero-spend env scrubbed.

    THE single choke point: both gate legs (pytest + hygiene suite) must go
    through this, so the scrub cannot be silently dropped from one call site.
    The --self-test canary spawns its child through this same function, which
    is what makes the wiring testable (and the guarantee structural).
    """
    env, _ = _zero_spend_env()
    return subprocess.run(
        args, cwd=str(project) if project is not None else None,
        capture_output=True, text=True, timeout=timeout, check=False,
        env=env,
    )


def self_test() -> int:
    """Canary — enforce the zero-spend guarantee as a test, not a one-off check.

    Forces every scrubbed credential name into os.environ (saving prior
    values) alongside an internal MCP_BRIDGE_SECRET, then proves THREE
    boundaries:

    1. `_zero_spend_env()` drops every paid credential.
    2. A real subprocess spawned through `_spawn` (the same choke point the
       gates use) sees every paid credential as CLEAN but the internal
       MCP_BRIDGE_SECRET as HAS — paid keys never reach subprocesses, the
       internal secret always does.
    3. The live-auth probe runs IN-PROCESS (urllib against os.environ, not a
       subprocess), so it carries MCP_BRIDGE_SECRET in its correct-secret
       request — while paid keys exist only in the probe's env, never in any
       subprocess env. Proved by capturing the exact headers the real
       `verify_live_auth` builds.

    Exit 0 = all boundaries enforced, 1 = broken.
    """
    saved = {k: os.environ.get(k) for k in (*ZERO_SPEND_ENV_VARS, _INTERNAL_SECRET)}
    for k in ZERO_SPEND_ENV_VARS:
        os.environ[k] = "self-test-sentinel"
    os.environ[_INTERNAL_SECRET] = "self-test-secret"
    failures: list[str] = []
    try:
        env, stripped = _zero_spend_env()
        # 1. Parent side: scrubbed names gone, internals preserved.
        for k in ZERO_SPEND_ENV_VARS:
            if k in env:
                failures.append(f"credential {k} survived _zero_spend_env()")
        for k in ("PATH", _INTERNAL_SECRET, "MSB_RAG_API_KEY", "OLLAMA_MODEL"):
            if k in os.environ and k not in env:
                failures.append(f"internal {k} was scrubbed (must survive)")

        # 2. Child side: spawned through the SAME choke point the gates use
        # (_spawn). Paid names must be CLEAN; the internal secret must be HAS.
        names = [*ZERO_SPEND_ENV_VARS, _INTERNAL_SECRET]
        child = _spawn([PY, "-c", _SELF_TEST_CHILD, *names], timeout=30)
        if child.returncode != 0:
            failures.append(f"self-test child crashed: {(child.stderr or '').strip()[:200]}")
        lines = child.stdout.splitlines()
        if len(lines) != len(names):
            failures.append(f"self-test child emitted {len(lines)} lines, expected {len(names)}")
        for line in lines:
            state, _, name = line.partition(" ")
            if name == _INTERNAL_SECRET:
                if state != "HAS":
                    failures.append(f"internal {_INTERNAL_SECRET} did NOT reach subprocess env (must survive)")
            elif state == "HAS":
                failures.append(f"credential {name} leaked into spawned subprocess env")

        # 3. Probe boundary: verify_live_auth is in-process urllib — it reads
        # MCP_BRIDGE_SECRET straight from os.environ and must carry it in the
        # correct-secret request. Capture the exact headers it sends (no
        # network: urlopen is stubbed; a nonexistent project forces the
        # os.environ fallback path).
        sent_headers: list[str | None] = []

        def _capture_probe(req, timeout=None):
            # urllib capitalizes header keys (x-mcp-secret -> X-mcp-secret),
            # so read case-insensitively.
            sent_headers.append(
                next((v for k, v in req.headers.items() if k.lower() == "x-mcp-secret"), None)
            )

            class _Resp:
                status = 200

                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

            return _Resp()

        saved_urlopen = urllib_request.urlopen
        urllib_request.urlopen = _capture_probe
        try:
            verify_live_auth(Path("/definitely-not-a-project"), live_auth=True)
        finally:
            urllib_request.urlopen = saved_urlopen
        if len(sent_headers) != 3:
            failures.append(f"probe sent {len(sent_headers)} requests, expected 3 (correct/wrong/missing)")
        else:
            if sent_headers[0] != "self-test-secret":
                failures.append(f"probe correct-secret request carried {sent_headers[0]!r}, expected the internal secret")
            if sent_headers[1] != "definitely-wrong-secret":
                failures.append(f"probe wrong-secret request carried {sent_headers[1]!r}")
            if sent_headers[2] is not None:
                failures.append(f"probe missing-secret request unexpectedly carried a header ({sent_headers[2]!r})")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if failures:
        for f in failures:
            print(f"[self-test] FAIL: {f}")
        print(f"[self-test] {len(failures)} failure(s) — zero-spend guarantee BROKEN")
        return 1
    print(f"[self-test] OK: {stripped} paid credentials stripped + invisible to subprocesses; "
          f"{_INTERNAL_SECRET} reaches subprocesses AND the in-process probe; internals + PATH preserved")
    return 0

# Member skills this factory can run for a project with the msb-v3 hygiene suite.
# Keys are the experiment_id values the runners actually emit (not CLI names);
# values are the actual standalone runner filenames (not derived, so the
# reproducibility check can never mismatch).
SUITE = {
    "h01_mcp_load": {"skill": "performance-hygiene", "runner": "h01_load_runner.py"},
    "h02_restart_hygiene": {"skill": "state-hygiene", "runner": "h02_restart_runner.py"},
    "h03_idempotency": {"skill": "api-hygiene", "runner": "h03_idempotency_runner.py"},
    "h04_race": {"skill": "concurrency-hygiene", "runner": "h04_race_runner.py"},
    "h05_contract_fuzzing": {"skill": "fuzzing", "runner": "h05_contract_fuzzing_runner.py"},
    "h06_audit_tampering": {"skill": "audit-hygiene", "runner": "h06_audit_tampering_runner.py"},
    "h07_auto_healing": {"skill": "self-healing", "runner": "h07_auto_healing_runner.py"},
    "h08_chaos": {"skill": "chaos", "runner": "h08_chaos_runner.py"},
    "h09_dependency_subtraction": {"skill": "dependency-hygiene", "runner": "h09_dependency_subtraction_runner.py"},
    "h10_resource_chaos": {"skill": "resource-exhaustion", "runner": "h10_resource_chaos_runner.py"},
}

RUNNER_FILES = [m["runner"] for m in SUITE.values()]

GATE_FIELDS = [
    "critical_requirements_tested",
    "critical_invariants_verified",
    "critical_failures_resolved",
    "security_boundaries_tested",
    "state_recovery_tested",
    "important_failure_modes_have_experiments",
    "claims_have_evidence",
    "regression_passed",
    "reproducibility_documented",
    "live_auth_verified",
    "unresolved_unknowns_disclosed",
]

_W = {"fail": 0, "partial": 1, "blocked": 2, "pass": 3, "unknown": 4}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_suite_config(project: Path) -> tuple[dict[str, dict[str, str]], bool, str]:
    """Load a per-project hygiene-suite config, with msb-v3 as the default.

    A project can declare <project>/scripts/hygiene/suite.json to describe
    its OWN experiments (multi-project support):

        {
          "experiments": {
            "s01_template_check": {"skill": "configuration-hygiene",
                                   "runner": "s01_template_check_runner.py"},
            ...
          },
          "live_auth": false,        // omit/true for projects with a server to probe
          "pytest_target": "tests/"  // optional; where pytest runs (default tests/)
        }

    Projects without a suite.json fall back to the built-in msb-v3 SUITE.
    Returns (experiments_map, live_auth_required, pytest_target).
    """
    cfg_path = project / "scripts" / "hygiene" / "suite.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except json.JSONDecodeError:
            print(f"[run_factory] WARN: malformed {cfg_path}; falling back to msb-v3 SUITE")
            return dict(SUITE), True, "tests/"
        experiments = cfg.get("experiments")
        target = str(cfg.get("pytest_target", "tests/"))
        if isinstance(experiments, dict) and experiments:
            return experiments, bool(cfg.get("live_auth", True)), target
        # A config typo must not silently re-enable the auth probe the project
        # opted out of — preserve the declared live_auth flag on the fallback.
        print(f"[run_factory] WARN: {cfg_path} has no usable experiments; falling back to msb-v3 SUITE")
        return dict(SUITE), bool(cfg.get("live_auth", True)), target
    return dict(SUITE), True, "tests/"


def load_dotenv(project: Path) -> dict[str, str]:
    """Load KEY=VALUE pairs from <project>/.env (no external dotenv dep)."""
    env: dict[str, str] = {}
    dotenv = project / ".env"
    if not dotenv.exists():
        return env
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def run_pytest(project: Path, target: str = "tests/") -> dict[str, Any]:
    """Run the project's real pytest suite and report whether it passed.

    This is the evidence behind `regression_passed`: previously the factory
    hardcoded False with a note in unresolved_unknowns; now it actually runs
    `pytest <target> -q` in the project root and records the outcome. The
    target defaults to `tests/` but can be overridden per-project via the
    suite.json `pytest_target` key (e.g. a repo whose tests live at the root).
    A suite that fails or times out keeps regression_passed=False and explains
    why.
    """
    started = dt.datetime.now(dt.timezone.utc)
    try:
        proc = _spawn([PY, "-m", "pytest", target, "-q"], project=project, timeout=900)
    except subprocess.TimeoutExpired:
        return {"passed": False, "summary": "pytest timed out after 900s", "duration_s": 900}
    duration_s = int((dt.datetime.now(dt.timezone.utc) - started).total_seconds())
    # Prefer the pytest count line ("N passed / N failed ...") as evidence;
    # the last non-empty line may be a warnings footer instead.
    summary = f"pytest exit {proc.returncode}"
    for line in ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines():
        if re.search(r"\d+\s+(passed|failed|error)", line):
            summary = line.strip()
            break
    return {
        "passed": proc.returncode == 0,
        "summary": summary[:300],
        "duration_s": duration_s,
    }


def verify_live_auth(project: Path, live_auth: bool = True) -> dict[str, Any]:
    """Probe the live server's x-mcp-secret auth gate end-to-end.

    The msb-v3 API gates /mcp/* behind the `x-mcp-secret` header
    (src/msb_v3/api/mcp_bridge.py). This probe proves the running server
    enforces it: correct secret -> 200, wrong secret -> 401, missing -> 401.
    Uses the project's .env MCP_BRIDGE_SECRET / MSB_BASE_URL (or env).
    Probes /mcp/tools — auth-gated AND read-only (the tool manifest), so the
    probe itself has no side effects.

    Projects that declare `live_auth: false` in suite.json (e.g. pure-CLI
    engines with no server) opt out: the probe is recorded as not-applicable
    rather than as an unresolved unknown.
    """
    if not live_auth:
        return {"verified": None, "detail": "scoped out — project declares live_auth:false in suite.json",
                "correct_secret": None, "wrong_secret": None, "missing_secret": None}

    env = load_dotenv(project)
    secret = env.get("MCP_BRIDGE_SECRET") or os.environ.get("MCP_BRIDGE_SECRET", "")
    base = env.get("MSB_BASE_URL") or os.environ.get("MSB_BASE_URL", "http://127.0.0.1:8766")
    url = f"{base}/mcp/tools"

    def probe(secret_header: str | None) -> int:
        headers = {"accept": "application/json"}
        if secret_header is not None:
            headers["x-mcp-secret"] = secret_header
        req = urllib_request.Request(url, headers=headers)
        try:
            with urllib_request.urlopen(req, timeout=15) as resp:
                return resp.status
        except HTTPError as e:
            return e.code
        except URLError:
            return 0  # unreachable

    if not secret:
        return {
            "verified": False, "detail": "no MCP_BRIDGE_SECRET configured in .env or env",
            "correct_secret": None, "wrong_secret": None, "missing_secret": None,
        }
    ok_code = probe(secret)
    wrong_code = probe("definitely-wrong-secret")
    missing_code = probe(None)
    verified = ok_code == 200 and wrong_code == 401 and missing_code == 401
    return {
        "verified": verified,
        "detail": f"correct->{ok_code} wrong->{wrong_code} missing->{missing_code}",
        "correct_secret": ok_code, "wrong_secret": wrong_code, "missing_secret": missing_code,
    }


def run_suite(project: Path) -> dict[str, Any]:
    """Run the project's hygiene_runner.py --all and return its aggregate."""
    runner = project / "scripts" / "hygiene" / "hygiene_runner.py"
    if not runner.exists():
        return {"available": False, "reason": f"no {runner} present"}
    proc = _spawn([PY, str(runner), "--all", "--json"], timeout=900)
    if proc.returncode not in (0, 1):  # 1 is a legit FAIL gate
        return {"available": True, "error": proc.stderr[-500:] or proc.stdout[-500:],
                "returncode": proc.returncode}
    last_json = _extract_json_object(proc.stdout)
    if isinstance(last_json, dict) and "results" in last_json:
        return {"available": True, "aggregate": last_json, "returncode": proc.returncode}
    return {"available": True, "aggregate": None, "returncode": proc.returncode,
            "error": (proc.stderr or proc.stdout or "").strip()[-300:]}


def _extract_json_object(text: str, key: str | None = "results") -> dict[str, Any] | None:
    """Parse the TOP-LEVEL JSON object in text that contains `key`.

    The suite runner prints one indented JSON object per experiment followed by
    the aggregate — so the last '{' is inside a NESTED object, not the root.
    This scans all complete top-level objects and returns the one containing
    the given key (or the last one if key is None).
    """
    raw = text.strip()
    if not raw:
        return None
    candidates: list[dict[str, Any]] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == "{":
            depth = 0
            for j in range(i, n):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(raw[i:j + 1])
                        except json.JSONDecodeError:
                            obj = None
                        if isinstance(obj, dict):
                            candidates.append(obj)
                        i = j + 1
                        break
            else:
                break
        else:
            i += 1
    if key is not None:
        for obj in candidates:
            if key in obj:
                return obj
    return candidates[-1] if candidates else None


def build_gate(results: list[dict[str, Any]], suite_verdict: str, project: Path,
               regression: dict[str, Any] | None = None,
               auth: dict[str, Any] | None = None,
               runner_files: list[str] | None = None) -> dict[str, Any]:
    """Map suite results onto the release-gate fields, honestly."""
    runner_files = runner_files or RUNNER_FILES
    regression = regression or {}
    auth = auth or {}
    gate = {k: False for k in GATE_FIELDS}
    if not results:
        # No evidence at all: every gate field must be False. A factory with no
        # runnable evidence cannot claim anything is resolved — but the pytest
        # and auth evidence is still reflected so the BLOCKED reason is honest.
        gate["regression_passed"] = bool(regression.get("passed"))
        # live_auth_verified is True only when the project opted into the probe
        # AND it passed; None (scoped out) is not an unknown.
        gate["live_auth_verified"] = bool(auth.get("verified")) if auth.get("verified") is not None else False
        unknowns = ["no member results — hygiene suite did not produce evidence"]
        if not gate["regression_passed"]:
            unknowns.append(f"project pytest suite did not pass in-factory ({regression.get('summary', 'not run')})")
        if auth.get("verified") is False:
            unknowns.append(f"live x-mcp-secret auth not verified ({auth.get('detail', 'not probed')})")
        return {**gate, "release_verdict": "BLOCKED", "unresolved_unknowns": unknowns}
    by_skill = {r["skill"]: r for r in results}
    # critical_requirements_tested: every member has an artifact
    gate["critical_requirements_tested"] = all("artifact" in r and r["artifact"] for r in results) if results else False
    # reproducibility_documented: every member's standalone runner file exists
    gate["reproducibility_documented"] = all(
        (project / "scripts" / "hygiene" / f).exists() for f in runner_files
    ) if runner_files else False
    # critical_invariants_verified: audit + state integrity pass
    gate["critical_invariants_verified"] = (
        by_skill.get("audit-hygiene", {}).get("verdict") == "pass"
        and by_skill.get("state-hygiene", {}).get("verdict") in ("pass", "blocked")
    )
    # critical_failures_resolved: no member fail
    gate["critical_failures_resolved"] = suite_verdict != "fail"
    # security_boundaries_tested: contract fuzzing + path-traversal cases pass
    gate["security_boundaries_tested"] = by_skill.get("fuzzing", {}).get("verdict") == "pass"
    # state_recovery_tested: restart + dependency-subtraction recovery
    gate["state_recovery_tested"] = (
        by_skill.get("dependency-hygiene", {}).get("verdict") == "pass"
        or by_skill.get("state-hygiene", {}).get("verdict") == "pass"
    )
    # important_failure_modes_have_experiments: every member ran (no unknowns)
    gate["important_failure_modes_have_experiments"] = (
        all(r.get("verdict") != "unknown" for r in results) if results else False
    )
    # claims_have_evidence: every result has an artifact path
    gate["claims_have_evidence"] = (
        all(r.get("artifact") for r in results) if results else False
    )
    # regression_passed: the project's REAL pytest suite, executed by this
    # factory (run_pytest). True only if `pytest tests/ -q` exits 0.
    gate["regression_passed"] = bool(regression.get("passed"))
    # live_auth_verified: the running server actually enforces x-mcp-secret
    # (verified against the live /mcp/tools endpoint, not just unit tests).
    # None = scoped out via suite.json (no server) — recorded, not an unknown.
    gate["live_auth_verified"] = bool(auth.get("verified")) if auth.get("verified") is not None else False
    # unresolved_unknowns_disclosed: schema violations + anything not proven
    gate["unresolved_unknowns_disclosed"] = True  # the unknowns list below is populated

    unknowns: list[str] = []
    if not gate["regression_passed"]:
        unknowns.append(
            f"project pytest suite did not pass in-factory "
            f"({regression.get('summary', 'not run')})"
        )
    if auth.get("verified") is False:
        unknowns.append(
            f"live x-mcp-secret auth not verified ({auth.get('detail', 'not probed')})"
        )

    verdict_map = {"fail": "FAILED", "blocked": "BLOCKED", "partial": "BLOCKED",
                   "pass": "PASS", "unknown": "UNKNOWN"}
    release = verdict_map.get(suite_verdict, "UNKNOWN")
    return {**gate, "release_verdict": release, "unresolved_unknowns": unknowns}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Engineering hygiene factory orchestrator")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--self-test", action="store_true",
                        help="canary: prove scrubbed credentials never reach subprocesses and the probe env is isolated")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    project: Path = args.project.resolve()
    project_map = {
        "project_id": __import__("hashlib").sha256(str(project).encode()).hexdigest()[:12],
        "name": project.name,
        "root": str(project),
        "discovered_at": now(),
    }
    evidence_dir = project / "artifacts" / "hygiene"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Per-project suite config: experiments map + whether a live server auth
    # probe applies + where pytest runs. Falls back to the built-in msb-v3
    # SUITE (pytest target defaults to tests/).
    suite_map, live_auth, pytest_target = load_suite_config(project)
    runner_files = [m.get("runner") for m in suite_map.values() if m.get("runner")]

    # Evidence for the two cross-cutting gate fields: real pytest run and a
    # live auth probe against the running server. Both run BEFORE the suite so
    # a healthy server is available for the auth check (the h02 restart
    # experiment SIGKILLs the listener mid-suite; after it the server is back,
    # but probing first avoids racing the restart).
    # Only run pytest when the project actually has the target (a project
    # without tests would exit 5 "no tests collected" and produce a confusing
    # regression unknown). The target defaults to tests/ but is per-project
    # overridable via suite.json `pytest_target` (e.g. root-level test files).
    pytest_path = project / pytest_target
    regression = run_pytest(project, pytest_target) if pytest_path.exists() else {
        "passed": False, "summary": f"no {pytest_target} in project"}
    auth = verify_live_auth(project, live_auth)
    print(f"[run_factory] pytest passed={regression['passed']} ({regression.get('summary')})")
    print(f"[run_factory] live auth verified={auth['verified']} ({auth.get('detail')})")

    # Record the scrub in the gate so the zero-spend guarantee is self-
    # documenting: the verdict carries how many paid-API keys were stripped
    # from subprocess envs on this run.
    _, stripped_count = _zero_spend_env()

    suite = run_suite(project)
    if not suite.get("available"):
        # Honest blocked: the factory cannot run members for this project.
        results = []
        for name, member in suite_map.items():
            results.append({
                "experiment": name, "skill": member.get("skill", "unknown"),
                "verdict": "blocked",
                "artifact": None, "reason": suite.get("reason", "no hygiene suite"),
            })
        suite_verdict = "blocked"
    else:
        results = []
        for r in (suite.get("aggregate") or {}).get("results", []):
            name = r.get("experiment")
            member = suite_map.get(name, {})
            results.append({
                "experiment": name,
                "skill": member.get("skill", "unknown"),
                "verdict": r.get("verdict", "unknown"),
                "artifact": r.get("artifact"),
                "violations": (validate_artifact_file(Path(r["artifact"]))
                               if r.get("artifact") and Path(r["artifact"]).exists() else []),
            })
        suite_verdict = (suite.get("aggregate") or {}).get("factory_verdict", "unknown")

    gate = build_gate(results, suite_verdict, project, regression, auth, runner_files)
    # Record the auth opt-out (if any) so a scoped-out field is never read as
    # "failed the probe" — it is a declared non-applicable.
    if auth.get("verified") is None:
        gate["live_auth_verified"] = False
        gate["unresolved_unknowns_disclosed"] = True
        gate.setdefault("notes", []).append(
            "live_auth scoped out: project suite.json declares live_auth:false (no server to probe)"
        )
    # Materialize schema-violation count into the gate for honesty.
    schema_violations = sum(len(r.get("violations", [])) for r in results)
    gate["artifact_schema_violations"] = schema_violations
    if stripped_count:
        gate.setdefault("notes", []).append(
            f"zero-spend env scrub: {stripped_count} paid-API credential(s) stripped "
            "from pytest + hygiene subprocess envs"
        )
    if schema_violations:
        gate["unresolved_unknowns"].append(
            f"{schema_violations} artifact schema violations (see per-result violations)"
        )

    result = {
        "PROJECT_MAP": project_map,
        "BASELINE": {
            "project": project_map,
            "tests": "n/a",
            "git": "n/a",
            "dependencies": "n/a",
            "claims": [],
        },
        "VERIFICATION": {
            "pytest": {"passed": regression["passed"], "summary": regression.get("summary"),
                        "duration_s": regression.get("duration_s")},
            "live_auth": {"verified": auth["verified"], "detail": auth.get("detail"),
                           "correct_secret": auth.get("correct_secret"),
                           "wrong_secret": auth.get("wrong_secret"),
                           "missing_secret": auth.get("missing_secret")},
        },
        "SUITE_CONFIG": {
            "source": "<project>/scripts/hygiene/suite.json"
                       if (project / "scripts" / "hygiene" / "suite.json").exists()
                       else "built-in msb-v3 SUITE",
            "experiments": list(suite_map),
            "live_auth": live_auth,
            "pytest_target": pytest_target,
        },
        "EVIDENCE_INDEX": {
            "claims_verified": len(results),
            "artifacts": [r.get("artifact") for r in results if r.get("artifact")],
            "verified_at": now(),
            "member_results": results,
        },
        "RELEASE_VERDICT": gate,
    }

    out = evidence_dir / "factory_gate.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"\n[run_factory] gate written to {out}")
    return 1 if gate["release_verdict"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
