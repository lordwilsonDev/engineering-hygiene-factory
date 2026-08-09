---
id: observability-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify logs, metrics, traces, alerts, and dashboards exist,
  are accurate, and trigger correctly.
inputs:
  - project_root
  - observability_stack
actions:
  - inspect logging
  - verify metrics
  - test alerting
  - verify dashboards
experiments:
  - log_completeness
  - metric_accuracy
  - alert_trigger
  - trace_correlation
evidence_required:
  - observability_results.json
  - alert_log.json
success_conditions:
  - all critical paths instrumented
  - alerts trigger correctly
failure_conditions:
  - missing logs
  - silent failures
  - false-negative alerts
artifacts:
  - observability_results.json
  - alert_log.json
---

# Observability Hygiene

## PURPOSE
Verify system observability.
