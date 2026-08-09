---
id: installation-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify installation, setup, and first-run experience on clean
  environments.
inputs:
  - project_root
  - install_instructions
actions:
  - test clean install
  - verify setup
  - test first run
experiments:
  - clean_install
  - setup_validation
  - first_run
  - dependency_bootstrap
evidence_required:
  - installation_results.json
  - setup_log.json
success_conditions:
  - installs cleanly
  - setup completes
  - first run succeeds
failure_conditions:
  - install fails
  - undocumented steps
  - missing dependencies
artifacts:
  - installation_results.json
  - setup_log.json
---

# Installation Hygiene

## PURPOSE
Verify install and setup paths.
