# Constellation Status (derived from evidence)

Generated: `2026-08-09T22:37:23.531065+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE.

Aggregate verdict: **UNVERIFIED**

| Project | State | Gate | Hygiene | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|
| msb-v3 | **STALE** | PASS | pass | True | 0.8h | success |
| agent-reach | **STALE** | PASS | pass | True | 2.6h | - |
| sovereign-mcp-os | **VERIFIED** | PASS | pass | True | 2.6h | success |
| sovereign-outcome-engine | **STALE** | PASS | pass | True | 2.6h | failure |
| nexus | **STALE** | PASS | pass | True | 2.0h | failure |
| domain-router | **VERIFIED** | PASS | pass | True | 0.6h | - |
| skill-orchestration-os | **UNVERIFIED** | - | - | - | Noneh | - |

## pytest summaries
- `msb-v3`: 256 passed, 2 warnings in 12.94s
- `agent-reach`: 428 passed in 12.61s
- `sovereign-mcp-os`: 22 passed in 0.24s
- `sovereign-outcome-engine`: 8 passed in 0.63s
- `nexus`: 4 passed in 0.96s
- `domain-router`: 23 passed in 0.12s

## Why
- `msb-v3`: gate artifact predates last commit
- `agent-reach`: gate artifact predates last commit
- `sovereign-mcp-os`: gate PASS, artifact age 2h
- `sovereign-outcome-engine`: gate artifact predates last commit
- `nexus`: gate artifact predates last commit
- `domain-router`: gate PASS, artifact age 0h
- `skill-orchestration-os`: no factory_gate.json artifact

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions). `--check` exits 1 if any present project is FAILING._