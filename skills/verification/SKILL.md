---
id: verification
family: hygiene
version: 0.0.1
objective: >
  Verify repairs, run regression, and confirm no new issues.
inputs:
  - repairs
  - baseline
actions:
  - run full test suite
  - compare to baseline
  - verify fixes
experiments:
  - regression_suite
  - fix_verification
  - baseline_comparison
evidence_required:
  - regression_results.json
  - baseline_diff.json
success_conditions:
  - all tests pass
  - no new regressions
  - fixes verified
failure_conditions:
  - regression failure
  - new issues
artifacts:
  - regression_results.json
  - baseline_diff.json
---

# Verification

## PURPOSE
Verify repairs and run regression.
