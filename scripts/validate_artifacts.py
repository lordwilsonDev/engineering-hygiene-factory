#!/usr/bin/env python3
"""Standalone artifact validator CLI.

Checks every evidence artifact under the project's artifacts/hygiene/ against
the factory experiment schema. Exits 0 when all artifacts conform, 1 when any
violation is found (malformed JSON, missing required field, wrong type, or an
out-of-enum verdict).

Usage:
  python scripts/validate_artifacts.py                    # default project (MSB_REPO)
  python scripts/validate_artifacts.py --evidence-dir /path/to/artifacts
  python scripts/validate_artifacts.py --schema verdict
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from schema_validate import validate_dir

DEFAULT_REPO = Path(os.environ.get("MSB_REPO", Path.home() / "msb-v3"))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate hygiene evidence artifacts against schemas")
    parser.add_argument("--evidence-dir", type=Path, default=None)
    parser.add_argument("--schema", default="experiment", choices=["experiment", "verdict"])
    args = parser.parse_args()

    evidence_dir = args.evidence_dir or (DEFAULT_REPO / "artifacts" / "hygiene")
    report = validate_dir(evidence_dir, args.schema)
    print(json.dumps(report, indent=2))
    return 0 if report["violation_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
