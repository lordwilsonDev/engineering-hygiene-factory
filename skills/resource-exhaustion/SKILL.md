---
id: resource-exhaustion
family: hygiene
version: 0.0.1
objective: >
  Verify system behavior under resource exhaustion: memory, disk,
  connections, file descriptors, threads.
inputs:
  - project_root
  - resource_limits
actions:
  - identify resource constraints
  - inject exhaustion
  - observe behavior
experiments:
  - memory_exhaustion
  - disk_full
  - connection_exhaustion
  - fd_exhaustion
  - thread_starvation
evidence_required:
  - resource_results.json
  - recovery_log.json
success_conditions:
  - graceful degradation
  - recovery after release
failure_conditions:
  - crash without recovery
  - data loss
artifacts:
  - resource_results.json
  - recovery_log.json
---

# Resource Exhaustion

## PURPOSE
Verify resilience to resource limits.
