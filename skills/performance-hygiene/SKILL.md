---
id: performance-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify latency, throughput, resource usage, and degradation
  patterns under expected and peak load.
inputs:
  - project_root
  - load_profile
actions:
  - run load tests
  - measure latency/throughput
  - identify degradation
experiments:
  - load_test
  - stress_test
  - spike_test
  - endurance_test
evidence_required:
  - performance_results.json
  - latency_distribution.json
success_conditions:
  - latency within SLA
  - throughput meets target
  - no resource leaks
failure_conditions:
  - SLA violation
  - throughput collapse
  - memory/connection leak
artifacts:
  - performance_results.json
  - latency_distribution.json
---

# Performance Hygiene

## PURPOSE
Verify performance under load.
