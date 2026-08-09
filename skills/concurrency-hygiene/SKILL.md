---
id: concurrency-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify thread safety, race condition handling, deadlock freedom,
  and consistent behavior under concurrent load.
inputs:
  - project_root
  - concurrency_model
actions:
  - identify shared state
  - run concurrent experiments
  - detect races/deadlocks
experiments:
  - concurrent_mutation
  - race_detection
  - deadlock_induction
  - throughput_degradation
evidence_required:
  - concurrency_results.json
  - race_report.json
success_conditions:
  - no data races
  - no deadlocks
  - throughput stable
failure_conditions:
  - data race detected
  - deadlock observed
  - throughput collapse
artifacts:
  - concurrency_results.json
  - race_report.json
---

# Concurrency Hygiene

## PURPOSE
Verify concurrent safety.

## EXECUTION
1. Identify shared mutable state.
2. Run concurrent mutations.
3. Detect races with instrumentation.
4. Record evidence.
