# Constellation Status (derived from evidence)

Generated: `2026-08-10T07:03:52.890394+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE.

Aggregate verdict: **STALE**

| Project | State | Gate | Hygiene | Mutation | Cov | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|---|---|
| nexus | **STALE** | PASS | pass | - | 61.0%/60% | True | 0.0h | - |

## pytest summaries
- `nexus`: 44 passed, 2 warnings in 2.59s

## Why
- `nexus`: gate recorded commit 71cc295f, code HEAD is fbd3d030 (code moved past the proof)

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions). `--check` exits 1 if any present project is FAILING._