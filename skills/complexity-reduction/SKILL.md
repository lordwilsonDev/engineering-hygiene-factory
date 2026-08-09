---
id: complexity-reduction
family: hygiene
version: 0.0.1
objective: >
  Identify unnecessary complexity, over-engineering, and
  simplification opportunities.
inputs:
  - project_root
actions:
  - measure complexity
  - identify hotspots
  - propose simplifications
experiments:
  - complexity_audit
  - dead_code_detection
  - simplification_validation
evidence_required:
  - complexity_report.json
  - simplification_proposals.md
success_conditions:
  - complexity within bounds
  - no dead code
  - simplifications validated
failure_conditions:
  - complexity growing
  - dead code present
artifacts:
  - complexity_report.json
  - simplification_proposals.md
---

# Complexity Reduction

## PURPOSE
Identify and reduce unnecessary complexity.
