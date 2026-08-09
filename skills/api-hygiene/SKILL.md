---
id: api-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify API contract stability, versioning, error handling,
  rate limiting, and backward compatibility.
inputs:
  - project_root
  - api_spec
actions:
  - enumerate endpoints
  - verify contracts
  - test error handling
  - test rate limits
experiments:
  - contract_validation
  - error_handling
  - rate_limit
  - version_compat
  - payload_fuzzing
evidence_required:
  - api_contract_results.json
  - error_handling_results.json
  - rate_limit_results.json
success_conditions:
  - all endpoints respond as specified
  - errors handled gracefully
  - rate limits enforced
failure_conditions:
  - undocumented behavior
  - unhandled exceptions
  - rate limit bypass
artifacts:
  - api_contract_results.json
  - error_handling_results.json
---

# API Hygiene

## PURPOSE
Verify API contracts and behavior.
