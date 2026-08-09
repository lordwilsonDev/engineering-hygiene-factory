---
id: dependency-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify dependency integrity, license compliance, known vulnerabilities,
  and behavior when dependencies are missing or modified.
inputs:
  - project_root
  - dependency_manifest
actions:
  - enumerate dependencies
  - check licenses
  - scan vulnerabilities
  - test subtraction
experiments:
  - dependency_scan
  - license_check
  - vuln_scan
  - subtraction_test
  - version_pin_test
evidence_required:
  - dependency_report.json
  - license_report.json
  - vuln_report.json
success_conditions:
  - no critical vulnerabilities
  - licenses compatible
  - subtraction tests pass
failure_conditions:
  - critical vuln
  - license conflict
  - hidden dependency
artifacts:
  - dependency_report.json
  - license_report.json
---

# Dependency Hygiene

## PURPOSE
Verify dependency health and integrity.
