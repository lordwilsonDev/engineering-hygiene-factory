# Constellation Status (derived from evidence)

Generated: `2026-08-09T23:43:59.709554+00:00` by `scripts/status_report.py`

**Nothing here is asserted — every state is derived from each project's `artifacts/hygiene/` gate artifacts and freshness vs its last git commit.** Missing or stale evidence shows as UNVERIFIED/STALE.

Aggregate verdict: **VERIFIED**

| Project | State | Gate | Hygiene | Mutation | pytest | Evidence age | CI (last run) |
|---|---|---|---|---|---|---|---|
| msb-v3 | **VERIFIED** | PASS | pass | - | True | 0.0h | - |

## pytest summaries
- `msb-v3`: 1 passed

## Why
- `msb-v3`: gate PASS, artifact age 0h

_Regenerate with: `python scripts/status_report.py` (add `--with-ci` for GitHub run conclusions). `--check` exits 1 if any present project is FAILING._