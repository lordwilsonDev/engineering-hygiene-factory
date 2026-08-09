---
id: test-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify the test suite covers critical paths, is not brittle,
  and produces reproducible results.
inputs:
  - project_root
  - test_command
actions:
  - run test suite
  - measure coverage
  - detect flaky tests
  - analyze assertion quality
experiments:
  - suite_run
  - flakiness_detection
  - coverage_mapping
  - assertion_audit
evidence_required:
  - test_results.json
  - coverage_report.json
  - flaky_tests.json
  - assertions_analysis.json
success_conditions:
  - all critical paths covered
  - zero flaky tests
  - coverage above threshold
failure_conditions:
  - critical path uncovered
  - flaky tests present
  - coverage below threshold
artifacts:
  - test_results.json
  - coverage_report.json
  - flaky_tests.json
---

# Test Hygiene

## PURPOSE
Verify test suite quality and coverage.

## EXECUTION
1. Run full test suite 10× to detect flakiness.
2. Measure coverage per module.
3. Audit assertions for strength.
4. Record results.

## DOGFOOD RULE
Factory test artifacts must themselves pass verification before release.
