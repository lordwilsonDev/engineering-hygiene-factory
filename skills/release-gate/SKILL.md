---
id: release-gate
family: hygiene
version: 0.0.1
objective: >
  Determine project readiness for release based on evidence,
  not prose or optimism.
inputs:
  - evidence_index
  - regression_results
  - unresolved_unknowns
actions:
  - evaluate release criteria
  - classify findings
  - emit verdict
experiments:
  - release_readiness_check
  - unknown_disclosure_audit
evidence_required:
  - RELEASE_VERDICT.json
  - FINAL_REPORT.md
success_conditions:
  - all critical criteria met
  - no UNKNOWN converted to PASS
failure_conditions:
  - critical criteria unmet
  - unknowns undisclosed
verdicts:
  - PASS
  - PASS_WITH_RISK
  - BLOCKED
  - FAILED
  - UNKNOWN
artifacts:
  - RELEASE_VERDICT.json
  - FINAL_REPORT.md
---

# Release Gate

## PURPOSE
Evidence-backed release verdict.

## EXECUTION
1. Evaluate all gate criteria.
2. If any critical unmet → BLOCKED.
3. If non-critical findings → PASS_WITH_RISK.
4. If all met → PASS.
5. NEVER convert UNKNOWN to PASS.

## DOGFOOD RULE
Factory must pass its own release gate before expanding to full 30+ skill set.
