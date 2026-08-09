---
id: disaster-recovery
family: hygiene
version: 0.0.1
objective: >
  Verify disaster recovery: RTO, RPO, failover, and data
  durability under catastrophic failure.
inputs:
  - project_root
  - dr_plan
actions:
  - define RTO/RPO
  - simulate disaster
  - measure recovery
  - verify data durability
experiments:
  - failover_test
  - rto_measurement
  - rpo_measurement
  - data_durability_check
evidence_required:
  - dr_results.json
  - rto_rpo_metrics.json
success_conditions:
  - RTO within target
  - RPO within target
  - no data loss
failure_conditions:
  - RTO exceeded
  - data loss
  - failover fails
artifacts:
  - dr_results.json
  - rto_rpo_metrics.json
---

# Disaster Recovery

## PURPOSE
Verify disaster recovery capabilities.
