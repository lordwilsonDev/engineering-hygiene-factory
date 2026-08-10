# Constellation Status (derived from evidence)

Generated: `2026-08-10T14:17:38.918239+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE; fresh PASS with a red repo CI shows as REGRESSED; a recorded post-gate failure shows as CONTESTED (contradictions are preserved, never silently discarded).

Aggregate verdict: **VERIFIED**

| Project | Tier | State | Gate | Hygiene | Mutation | Cov | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|---|---|---|
| msb-v3 | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 70.8% | 70.0%/65% | True | 1.0h | success |
| agent-reach | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 67.5% | 84.0%/75% | True | 7.2h | success |
| sovereign-mcp-os | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 66.7% | 94.0%/90% | True | 0.4h | success |
| sovereign-outcome-engine | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 55.0% | 74.0%/70% | True | 0.0h | - |
| nexus | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 50.7% | 61.0%/60% | True | 0.4h | success |
| domain-router | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 56.9% | - | True | 0.1h | - |
| skill-orchestration-os | T5 ADVERSARIAL | **VERIFIED** | PASS | pass | 52.7% | - | True | 0.1h | - |

## pytest summaries
- `msb-v3`: 282 passed, 2 warnings in 21.56s
- `agent-reach`: 599 passed in 14.56s
- `sovereign-mcp-os`: 22 passed in 0.54s
- `sovereign-outcome-engine`: 64 passed in 0.88s
- `nexus`: 44 passed, 2 warnings in 2.59s
- `domain-router`: 23 passed in 0.13s
- `skill-orchestration-os`: 16 passed, 2 warnings in 0.63s

## Why
- `msb-v3`: gate PASS, artifact age 0h
- `agent-reach`: gate PASS, artifact age 7h
- `sovereign-mcp-os`: gate PASS, artifact age 0h
- `sovereign-outcome-engine`: gate PASS, artifact age 0h
- `nexus`: gate PASS, artifact age 0h
- `domain-router`: gate PASS, artifact age 0h
- `skill-orchestration-os`: gate PASS, artifact age 0h

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions — required for REGRESSED to be derivable). `--check` exits 1 if any present project is FAILING._