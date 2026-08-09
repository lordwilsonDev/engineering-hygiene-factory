---
id: documentation-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify documentation exists, is accurate, and matches code behavior.
inputs:
  - project_root
actions:
  - enumerate docs
  - verify claims against code
  - check completeness
experiments:
  - doc_accuracy
  - claim_verification
  - completeness_check
evidence_required:
  - doc_audit.json
  - claim_mapping.yaml
success_conditions:
  - docs match code
  - all critical paths documented
failure_conditions:
  - undocumented behavior
  - stale docs
  - missing README
artifacts:
  - doc_audit.json
  - claim_mapping.yaml
---

# Documentation Hygiene

## PURPOSE
Verify documentation accuracy.
