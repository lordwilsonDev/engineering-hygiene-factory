---
id: test-the-tests
family: hygiene
version: 0.0.1
objective: >
  Verify the test suite itself is correct: no false positives,
  no false negatives, no tautological assertions.
inputs:
  - project_root
  - test_command
actions:
  - inject faults into code
  - verify tests catch them
  - check for tautologies
experiments:
  - fault_injection
  - false_positive_detection
  - tautology_detection
  - assertion_quality
evidence_required:
  - test_quality_results.json
  - fault_detection_report.json
success_conditions:
  - tests catch injected faults
  - no tautological assertions
failure_conditions:
  - fault not caught
  - false positives
  - tautological assertions
artifacts:
  - test_quality_results.json
  - fault_detection_report.json
---

# Test the Tests

## PURPOSE
Verify test suite correctness.
