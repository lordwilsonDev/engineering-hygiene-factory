---
id: reproducibility
family: hygiene
version: 0.0.1
objective: >
  Verify builds, tests, and deployments are deterministic and
  reproducible from source.
inputs:
  - project_root
  - build_script
actions:
  - capture build environment
  - reproduce build
  - compare artifacts
experiments:
  - build_reproducibility
  - test_reproducibility
  - deploy_reproducibility
evidence_required:
  - reproducibility_results.json
  - artifact_checksums.json
success_conditions:
  - identical artifacts
  - deterministic tests
failure_conditions:
  - non-deterministic build
  - flaky tests
artifacts:
  - reproducibility_results.json
  - artifact_checksums.json
---

# Reproducibility

## PURPOSE
Verify deterministic builds and tests.
