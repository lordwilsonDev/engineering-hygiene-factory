---
id: repair
family: hygiene
version: 0.0.1
objective: >
  Execute repairs for findings, verify fixes, and prevent regression.
  Optimize for maximum verified recovery with minimum unauthorized intervention.
inputs:
  - findings
  - repair_strategies
actions:
  - prioritize findings
  - apply fixes
  - verify fixes
  - run regression
experiments:
  - fix_verification
  - regression_test
  - precision_repair_measurement
evidence_required:
  - repairs.json
  - verification_results.json
  - regression_results.json
success_conditions:
  - findings resolved
  - regression passes
  - no new issues
failure_conditions:
  - fix incomplete
  - regression fails
  - new issues introduced
artifacts:
  - repairs.json
  - verification_results.json
---

# Repair

## PURPOSE
Execute and verify repairs for findings.
