---
id: state-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify state persistence, recovery, consistency, and idempotency
  across restarts and failures.
inputs:
  - project_root
  - state_schema
actions:
  - inspect persistence layer
  - test restart recovery
  - verify state consistency
experiments:
  - restart_recovery
  - state_consistency
  - idempotency
  - partial_write_recovery
evidence_required:
  - state_recovery_results.json
  - consistency_checks.json
success_conditions:
  - state recovers after restart
  - no partial writes
  - idempotent operations
failure_conditions:
  - state loss on restart
  - partial writes undetected
  - non-idempotent mutations
artifacts:
  - state_recovery_results.json
  - consistency_checks.json
---

# State Hygiene

## PURPOSE
Verify state persistence and recovery.

## EXECUTION
1. Capture state baseline.
2. Kill/restart system.
3. Verify state recovered.
4. Test idempotency: repeat operation, count mutations.
