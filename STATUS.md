# Constellation Status (derived from evidence)

Generated: `2026-08-10T13:22:34.877814+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE; fresh PASS with a red repo CI shows as REGRESSED; a recorded post-gate failure shows as CONTESTED (contradictions are preserved, never silently discarded).

Aggregate verdict: **VERIFIED**

| Project | Tier | State | Gate | Hygiene | Mutation | Cov | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|---|---|---|
| msb-v3 | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 70.8% | 70.0%/65% | True | 0.1h | - |
| agent-reach | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 67.5% | 84.0%/75% | True | 6.3h | - |
| sovereign-mcp-os | T4 INTEGRATED | **VERIFIED** | PASS | pass | - | 94.0%/90% | True | 0.3h | - |
| sovereign-outcome-engine | T4 INTEGRATED | **VERIFIED** | PASS | pass | - | 77.0%/70% | True | 0.3h | - |
| nexus | T4 INTEGRATED | **VERIFIED** | PASS | pass | - | 61.0%/60% | True | 5.3h | - |
| domain-router | T4 INTEGRATED | **VERIFIED** | PASS | pass | - | - | True | 5.3h | - |
| skill-orchestration-os | T4 INTEGRATED | **VERIFIED** | PASS | pass | - | - | True | 5.3h | - |

## pytest summaries
- `msb-v3`: 282 passed, 2 warnings in 21.56s
- `agent-reach`: 599 passed in 14.56s
- `sovereign-mcp-os`: 22 passed in 0.63s
- `sovereign-outcome-engine`: 64 passed in 0.98s
- `nexus`: 44 passed, 2 warnings in 2.70s
- `domain-router`: 23 passed in 0.14s
- `skill-orchestration-os`: 16 passed, 2 warnings in 0.52s

## Why
- `msb-v3`: gate PASS, artifact age 0h
- `agent-reach`: gate PASS, artifact age 6h
- `sovereign-mcp-os`: gate PASS, artifact age 0h
- `sovereign-outcome-engine`: gate PASS, artifact age 0h
- `nexus`: gate PASS, artifact age 5h
- `domain-router`: gate PASS, artifact age 5h
- `skill-orchestration-os`: gate PASS, artifact age 5h

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions — required for REGRESSED to be derivable). `--check` exits 1 if any present project is FAILING._