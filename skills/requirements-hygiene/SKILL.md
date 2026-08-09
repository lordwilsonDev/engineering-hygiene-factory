---
id: requirements-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify that project requirements, contracts, and invariants are
  explicitly stated, testable, and not silently violated.
inputs:
  - project_root
  - contract_spec
actions:
  - parse declared requirements
  - enumerate implicit invariants
  - build requirement coverage map
experiments:
  - contract_satisfaction
  - invariant_regression
  - silent_requirement_drift
evidence_required:
  - requirement_coverage.yaml
  - invariant_test_results.json
success_conditions:
  - all critical requirements have at least one experiment
  - no silent requirement drift detected
failure_conditions:
  - critical requirement untested
  - invariant violated without detection
artifacts:
  - requirement_coverage.yaml
  - invariant_test_results.json
---

# Requirements Hygiene

## PURPOSE
Verify requirements, contracts, and invariants are explicit, testable, and enforced.

## EXECUTION
1. Enumerate requirements from README, SPEC, contracts, APIs.
2. For each requirement: define experiment, expected behavior, evidence command.
3. Run experiment; record 13-field evidence.
4. If drift detected: emit finding, propose repair, re-verify.

## DOGFOOD RULE
This skill must be used to verify its own requirement coverage before release.
