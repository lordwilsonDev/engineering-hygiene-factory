#!/usr/bin/env python3
"""Business-deliverable claim container validator (blueprint P2 producer adapter).

The last blueprint producer is the BUSINESS deliverable: an outcome report is
a bundle of claims ("the scan was read-only", "the Data ROI score is 62",
"the deal terms are X"). sovereign-outcome-engine emits a machine-readable
claim container next to each report (artifacts/business/claim_container_*.json).

This adapter validates any claim container against the contract so a
deliverable's claims can be checked BEFORE the ledger would trust them:

  contract = {
    deliverable_id: str, deliverable_type: str, produced_by: str,
    generated_at: str, claims: [{
      claim_id: str, subject: str, claim_type: str, assertion: str,
      verification_tier: T0..T6, verdict: str, evidence: [{path, kind}],
      evaluated_at: str,
    }]
  }

Checks (each violation is reported; exit 1 on any violation):
  - container parses as JSON with required top-level fields
  - claims is a non-empty list
  - every claim has required fields with correct types
  - verification_tier is one of T0..T6 (never over-claimed)
  - every evidence path exists relative to the container's repo root
    (or is exempt as a non-filesystem reference)

Usage:
  python scripts/validate_claim_containers.py --dir /path/to/artifacts/business
  python scripts/validate_claim_containers.py --file /path/to/claim_container.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_TIERS = {f"T{i}" for i in range(7)}
# Ledger verdict enum (status_report.py states + the blueprint's claim states).
# A claim verdict outside this set is an assertion the ledger never made.
VALID_VERDICTS = {
    "VERIFIED", "FAILING", "STALE", "UNVERIFIED", "REGRESSED", "CONTESTED",
    "INCONCLUSIVE", "UNKNOWN",
}
REQUIRED_TOP = {"deliverable_id", "deliverable_type", "produced_by", "generated_at", "claims"}
REQUIRED_CLAIM = {"claim_id", "subject", "claim_type", "assertion",
                  "verification_tier", "verdict", "evidence", "evaluated_at"}


def validate_container(path: Path, repo_root: Path | None = None) -> dict:
    violations: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"file": str(path), "violations": [f"invalid JSON: {e}"], "violation_count": 1}

    root = repo_root or path.resolve().parent.parent.parent  # artifacts/business -> repo root
    missing_top = REQUIRED_TOP - set(data)
    if missing_top:
        violations.append(f"missing top-level fields: {sorted(missing_top)}")
    if "deliverable_id" in data and not isinstance(data["deliverable_id"], str):
        violations.append("deliverable_id must be a string")

    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        violations.append("claims must be a non-empty list")
        claims = []
    for i, c in enumerate(claims):
        label = f"claims[{i}]"
        if not isinstance(c, dict):
            violations.append(f"{label} must be an object")
            continue
        missing = REQUIRED_CLAIM - set(c)
        if missing:
            violations.append(f"{label} missing fields: {sorted(missing)}")
        tier = c.get("verification_tier")
        if tier not in VALID_TIERS:
            violations.append(f"{label}.verification_tier={tier!r} not in T0..T6")
        verdict = c.get("verdict")
        if not isinstance(verdict, str) or verdict.upper() not in VALID_VERDICTS:
            violations.append(f"{label}.verdict={verdict!r} not in ledger verdict enum")
        evidence = c.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            violations.append(f"{label}.evidence must be a non-empty list")
            evidence = []
        for e in evidence:
            if not isinstance(e, dict) or "path" not in e:
                violations.append(f"{label}.evidence entry missing 'path'")
                continue
            ev_path = Path(e["path"])
            if not (root / ev_path).exists() and not ev_path.is_absolute():
                violations.append(f"{label}.evidence path not found: {e['path']}")

    return {"file": str(path), "violations": violations, "violation_count": len(violations)}


def validate_dir(d: Path, repo_root: Path | None = None) -> dict:
    files = sorted(d.glob("claim_container_*.json"))
    if not files:
        return {"dir": str(d), "files": [], "violations": ["no claim_container_*.json found"],
                "violation_count": 1}
    total = 0
    all_violations: list[dict] = []
    for f in files:
        r = validate_container(f, repo_root)
        total += r["violation_count"]
        all_violations.append(r)
    return {"dir": str(d), "files": [str(f) for f in files],
            "violations": all_violations, "violation_count": total}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate business-deliverable claim containers")
    ap.add_argument("--file", type=Path, default=None, help="single claim container file")
    ap.add_argument("--dir", type=Path, default=None, help="directory of claim_container_*.json")
    ap.add_argument("--repo-root", type=Path, default=None, help="repo root for evidence-path checks")
    args = ap.parse_args()

    if args.file:
        report = validate_container(args.file, args.repo_root)
    elif args.dir:
        report = validate_dir(args.dir, args.repo_root)
    else:
        print("usage: --file <path> or --dir <path>")
        return 2

    print(json.dumps(report, indent=2))
    return 0 if report["violation_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
