---
id: determinism
family: hygiene
version: 0.0.1
objective: >
  Verify that deterministic operations produce identical outputs
  given identical inputs and environment state.
inputs:
  - project_root
  - deterministic_operations
actions:
  - identify deterministic operations
  - run repeated trials
  - compare outputs
experiments:
  - output_equality
  - seed_sensitivity
  - ordering_independence
  - timestamp_independence
evidence_required:
  - determinism_results.json
  - variance_report.json
success_conditions:
  - outputs identical
  - no hidden nondeterminism
failure_conditions:
  - output variance
  - order-dependent behavior
  - time-dependent behavior
artifacts:
  - determinism_results.json
  - variance_report.json
---

# Determinism

## PURPOSE
Verify deterministic behavior.
