---
id: configuration-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify configuration is valid, documented, secure, and behaves
  correctly under misconfiguration.
inputs:
  - project_root
  - config_schema
actions:
  - enumerate config files
  - validate against schema
  - test defaults
  - inject misconfigurations
experiments:
  - config_validation
  - missing_config
  - invalid_config
  - secret_exposure
  - env_override
evidence_required:
  - config_validation_results.json
  - misconfiguration_results.json
success_conditions:
  - all configs valid
  - secrets not exposed
  - sensible defaults
failure_conditions:
  - invalid config accepted
  - secret in logs
  - undocumented env vars
artifacts:
  - config_validation_results.json
  - misconfiguration_results.json
---

# Configuration Hygiene

## PURPOSE
Verify configuration correctness and security.
