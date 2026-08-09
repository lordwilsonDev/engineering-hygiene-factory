"""Security Hygiene Skill — claim registry."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CLAIMS: list[dict[str, Any]] = [
    {
        "id": "SEC-001",
        "statement": "/mcp endpoints reject requests without valid x-mcp-secret",
        "status": "UNKNOWN",
        "evidence_refs": [],
        "experiments": ["H11"],
        "severity": "critical",
    },
    {
        "id": "SEC-002",
        "statement": "Audit chain detects text alteration",
        "status": "OBSERVED",
        "evidence_refs": [],
        "experiments": ["H06"],
        "severity": "high",
    },
    {
        "id": "SEC-003",
        "statement": "Audit chain recovers from detected tampering",
        "status": "FALSIFIED",
        "evidence_refs": [],
        "experiments": ["H06"],
        "severity": "high",
    },
    {
        "id": "SEC-004",
        "statement": "/register rejects payloads > N bytes",
        "status": "FALSIFIED",
        "evidence_refs": [],
        "experiments": ["H10"],
        "severity": "medium",
    },
    {
        "id": "SEC-005",
        "statement": "Truth registry directory removal triggers graceful degradation",
        "status": "TESTED",
        "evidence_refs": [],
        "experiments": ["H09"],
        "severity": "medium",
    },
    {
        "id": "SEC-006",
        "statement": "Idempotent replay does not duplicate truth entries",
        "status": "TESTED",
        "evidence_refs": [],
        "experiments": ["H03"],
        "severity": "low",
    },
    {
        "id": "SEC-007",
        "statement": "System survives controlled restart without state loss",
        "status": "TESTED",
        "evidence_refs": [],
        "experiments": ["H02"],
        "severity": "high",
    },
]


def load_claims(path: str | Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        path = Path(__file__).parent / "security_claims.json"
    p = Path(path)
    if not p.exists():
        return [c.copy() for c in DEFAULT_CLAIMS]
    return json.loads(p.read_text()).get("claims", [])


def save_claims(claims: list[dict[str, Any]], path: str | Path | None = None) -> None:
    if path is None:
        path = Path(__file__).parent / "security_claims.json"
    Path(path).write_text(json.dumps({"claims": claims}, indent=2))
