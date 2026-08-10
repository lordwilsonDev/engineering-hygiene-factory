# Constellation Status (derived from evidence)

Generated: `2026-08-10T07:12:47.943594+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE.

Aggregate verdict: **VERIFIED**

| Project | State | Gate | Hygiene | Mutation | Cov | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|---|---|
| msb-v3 | **VERIFIED** | PASS | pass | - | 70.0%/65% | True | 0.2h | - |
| agent-reach | **VERIFIED** | PASS | pass | 67.5% | 84.0%/75% | True | 0.2h | - |
| sovereign-mcp-os | **VERIFIED** | PASS | pass | - | 94.0%/85% | True | 0.2h | - |
| sovereign-outcome-engine | **VERIFIED** | PASS | pass | - | 77.0%/65% | True | 0.2h | - |
| nexus | **VERIFIED** | PASS | pass | - | 61.0%/60% | True | 0.2h | - |
| domain-router | **VERIFIED** | PASS | pass | - | - | True | 0.0h | - |
| skill-orchestration-os | **VERIFIED** | PASS | pass | - | - | True | 0.0h | - |

## pytest summaries
- `msb-v3`: 261 passed, 2 warnings in 23.23s
- `agent-reach`: 599 passed in 14.56s
- `sovereign-mcp-os`: 22 passed in 0.56s
- `sovereign-outcome-engine`: 64 passed in 0.95s
- `nexus`: 44 passed, 2 warnings in 2.59s
- `domain-router`: 23 passed in 0.13s
- `skill-orchestration-os`: 15 passed, 2 warnings in 0.50s

## Why
- `msb-v3`: gate PASS, artifact age 0h
- `agent-reach`: gate PASS, artifact age 0h
- `sovereign-mcp-os`: gate PASS, artifact age 0h
- `sovereign-outcome-engine`: gate PASS, artifact age 0h
- `nexus`: gate PASS, artifact age 0h
- `domain-router`: gate PASS, artifact age 0h
- `skill-orchestration-os`: gate PASS, artifact age 0h

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions). `--check` exits 1 if any present project is FAILING._