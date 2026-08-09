---
id: data-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify data integrity, schema enforcement, migrations,
  backup/restore, and corruption detection.
inputs:
  - project_root
  - schema
actions:
  - inspect data layer
  - verify schema enforcement
  - test migrations
  - test backup/restore
experiments:
  - schema_validation
  - migration_rollback
  - backup_restore
  - corruption_detection
  - data_retention
evidence_required:
  - data_integrity_results.json
  - migration_results.json
  - backup_restore_results.json
success_conditions:
  - schema enforced
  - migrations reversible
  - backup/restore verified
failure_conditions:
  - schema violation undetected
  - data loss on migration
  - backup corrupt
artifacts:
  - data_integrity_results.json
  - migration_results.json
---

# Data Hygiene

## PURPOSE
Verify data integrity and lifecycle.
