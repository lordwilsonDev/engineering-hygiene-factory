---
id: human-factors
family: hygiene
version: 0.0.1
objective: >
  Verify system usability, error messages, documentation clarity,
  and operational runbooks for human operators.
inputs:
  - project_root
  - operator_guide
actions:
  - review UX
  - test error messages
  - verify runbooks
  - assess cognitive load
experiments:
  - error_message_quality
  - runbook_validation
  - cognitive_load_assessment
  - onboarding_test
evidence_required:
  - human_factors_results.json
  - error_message_audit.json
success_conditions:
  - clear error messages
  - runbooks accurate
  - onboarding succeeds
failure_conditions:
  - cryptic errors
  - stale runbooks
  - high cognitive load
artifacts:
  - human_factors_results.json
  - error_message_audit.json
---

# Human Factors

## PURPOSE
Verify system usability for operators.
