---
id: self-healing
family: hygiene
version: 0.0.1
objective: >
  Verify system can detect and recover from failures with
  maximum verified recovery and minimum unauthorized intervention.
inputs:
  - project_root
  - failure_modes
actions:
  - inject failures
  - observe recovery
  - measure precision/false repair
experiments:
  - auto_recovery
  - precision_repair
  - false_repair_detection
  - unauthorized_intervention_detection
evidence_required:
  - healing_results.json
  - precision_report.json
success_conditions:
  - recovery succeeds
  - precision_repair high
  - false_repair low
failure_conditions:
  - recovery fails
  - high false repair rate
  - unauthorized intervention
artifacts:
  - healing_results.json
  - precision_report.json
---

# Self-Healing

## PURPOSE
Verify auto-recovery with minimal intervention.

## METRICS
- Precision_repair = correct repairs / all repairs
- FalseRepairRate = harmful repairs / all repairs
- Optimize for verified recovery, not repair count.
