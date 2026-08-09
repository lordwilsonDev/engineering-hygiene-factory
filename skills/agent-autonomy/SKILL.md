---
id: agent-autonomy
family: hygiene
version: 0.0.1
objective: >
  Verify agent behavior: tool selection, autonomy boundaries,
  error recovery, and goal completion without unauthorized action.
inputs:
  - project_root
  - agent_spec
actions:
  - define autonomy boundary
  - inject edge cases
  - verify bounded behavior
experiments:
  - boundary_enforcement
  - error_recovery
  - goal_completion
  - unauthorized_action_detection
evidence_required:
  - autonomy_results.json
  - boundary_violations.json
success_conditions:
  - respects boundaries
  - recovers from errors
  - completes goals
failure_conditions:
  - boundary violation
  - goal abandonment
  - unauthorized action
artifacts:
  - autonomy_results.json
  - boundary_violations.json
---

# Agent Autonomy

## PURPOSE
Verify agent behavior within boundaries.
