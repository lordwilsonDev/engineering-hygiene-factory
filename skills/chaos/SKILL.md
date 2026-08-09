---
id: chaos
family: hygiene
version: 0.0.1
objective: >
  Verify system behavior under chaotic conditions: random failures,
  network partitions, and cascading failures.
inputs:
  - project_root
  - chaos_scope
actions:
  - define blast radius
  - inject chaos
  - observe cascade
experiments:
  - network_partition
  - node_failure
  - cascading_failure
  - random_failure
evidence_required:
  - chaos_results.json
  - cascade_report.json
success_conditions:
  - graceful degradation
  - no data loss
  - recovery within SLA
failure_conditions:
  - cascading collapse
  - data loss
  - unrecoverable state
artifacts:
  - chaos_results.json
  - cascade_report.json
---

# Chaos Engineering

## PURPOSE
Verify resilience under chaotic conditions.
