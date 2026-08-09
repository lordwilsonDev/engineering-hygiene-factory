"""Shared artifact-schema validation for the engineering hygiene factory.

Loads the schemas in `../schemas/` (experiment.yaml, verdict.yaml) and checks
evidence artifacts against them: required fields, field types, and enums.
The factory aggregator (`run_factory.py`) and the standalone validator
(`validate_artifacts.py`) both use this module so there is one source of
truth for "what a valid artifact looks like".

Dependency note: PyYAML is required (available in the hermes python env).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover - defensive
    yaml = None

FACTORY_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = FACTORY_ROOT / "schemas"

SCHEMA_KEYS = {
    "experiment": {"fields": "fields", "name": "name"},
    "verdict": {"fields": "fields", "name": "name"},
}


def load_schema(name: str) -> Dict[str, Any]:
    """Load a schema yaml into a dict of {field_id: {type, required, enum}}."""
    if yaml is None:
        raise RuntimeError("PyYAML is required for schema validation (import yaml failed)")
    path = SCHEMAS_DIR / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields: Dict[str, Any] = {}
    for f in raw.get("fields", []):
        fields[f["id"]] = {
            "type": f.get("type", "string"),
            "required": f.get("required", False),
            "enum": f.get("enum", None),
        }
    return fields


def _type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array[string]":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if expected_type == "array[object]":
        return isinstance(value, list) and all(isinstance(v, dict) for v in value)
    return True  # unknown schema type: do not fail closed on schema typos


def validate_artifact(artifact: Dict[str, Any], schema_name: str = "experiment") -> List[str]:
    """Validate one artifact dict against the named schema.

    Returns a list of human-readable violations (empty list == valid).
    """
    fields = load_schema(schema_name)
    violations: List[str] = []
    for field_id, spec in fields.items():
        if spec["required"] and field_id not in artifact:
            violations.append(f"missing required field: {field_id}")
            continue
        if field_id not in artifact:
            continue
        if artifact[field_id] is None and not spec["required"]:
            # null on an optional field == absent; only required fields must be typed
            continue
        if not _type_matches(artifact[field_id], spec["type"]):
            violations.append(
                f"field {field_id}: expected {spec['type']}, got "
                f"{type(artifact[field_id]).__name__}"
            )
            continue
        if spec["enum"] is not None and artifact[field_id] not in spec["enum"]:
            violations.append(
                f"field {field_id}: value {artifact[field_id]!r} not in "
                f"allowed enum {spec['enum']}"
            )
    return violations


def validate_artifact_file(path: Path, schema_name: str = "experiment") -> List[str]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"not valid JSON: {e}"]
    return validate_artifact(artifact, schema_name)


def validate_dir(evidence_dir: Path, schema_name: str = "experiment") -> Dict[str, Any]:
    """Validate every *.json artifact in a directory. Returns a report dict."""
    files = sorted(evidence_dir.glob("*.json"))
    report = {
        "schema": schema_name,
        "evidence_dir": str(evidence_dir),
        "scanned": len(files),
        "valid": [],
        "violations": {},
        "valid_count": 0,
        "violation_count": 0,
    }
    for p in files:
        violations = validate_artifact_file(p, schema_name)
        if violations:
            report["violations"][str(p)] = violations
            report["violation_count"] += 1
        else:
            report["valid"].append(str(p))
            report["valid_count"] += 1
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate hygiene evidence artifacts against schemas")
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="directory of artifacts (default: resolve via MSB_REPO)")
    parser.add_argument("--schema", default="experiment", choices=["experiment", "verdict"])
    args = parser.parse_args()

    evidence_dir = args.evidence_dir
    if evidence_dir is None:
        repo = Path(__import__("os").environ.get("MSB_REPO", "")) or Path.home() / "msb-v3"
        evidence_dir = repo / "artifacts" / "hygiene"

    report = validate_dir(evidence_dir, args.schema)
    print(json.dumps(report, indent=2))
    return 0 if report["violation_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
