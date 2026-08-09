---
id: audit-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify audit logs are complete, immutable, tamper-evident,
  and contain sufficient detail for forensic analysis.
inputs:
  - project_root
  - audit_policy
actions:
  - inspect audit system
  - verify completeness
  - test tamper detection
  - test retention
experiments:
  - audit_completeness
  - tamper_detection
  - retention_policy
  - log_correlation
evidence_required:
  - audit_results.json
  - tamper_report.json
success_conditions:
  - all actions logged
  - tampering detected
  - retention enforced
failure_conditions:
  - missing audit entries
  - tampering undetected
  - logs mutable
artifacts:
  - audit_results.json
  - tamper_report.json
---

# Audit Hygiene

## PURPOSE
Verify audit log integrity.
