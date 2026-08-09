---
id: migration-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify schema migrations, data migrations, and backward compatibility
  across versions.
inputs:
  - project_root
  - migration_history
actions:
  - inspect migrations
  - test forward/backward
  - verify zero-downtime
experiments:
  - forward_migration
  - backward_migration
  - zero_downtime
  - dirty_state_recovery
evidence_required:
  - migration_results.json
  - compatibility_matrix.json
success_conditions:
  - migrations reversible
  - backward compatible
  - zero downtime
failure_conditions:
  - data loss on migration
  - incompatible versions
artifacts:
  - migration_results.json
  - compatibility_matrix.json
---

# Migration Hygiene

## PURPOSE
Verify migration safety.
