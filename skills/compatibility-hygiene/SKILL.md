---
id: compatibility-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify behavior across runtime versions, OS versions, architectures,
  and dependent service versions.
inputs:
  - project_root
  - compatibility_matrix
actions:
  - enumerate runtime deps
  - test version matrix
  - document support
experiments:
  - version_matrix
  - platform_compat
  - api_compat
evidence_required:
  - compatibility_results.json
  - support_matrix.yaml
success_conditions:
  - supported versions verified
  - breaking changes documented
failure_conditions:
  - silent version break
  - undocumented incompatibility
artifacts:
  - compatibility_results.json
  - support_matrix.yaml
---

# Compatibility Hygiene

## PURPOSE
Verify cross-version/ platform compatibility.
