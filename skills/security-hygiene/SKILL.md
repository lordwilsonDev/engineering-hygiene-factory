---
id: security-hygiene
family: hygiene
version: 0.1.0
author: Wilson
status: active
objective: Challenge security claims with adversarial mutations under restorable isolation.
mutations:
  - id: audit_chain_tampering
    alias: H06
    risk: high
    status: implemented
  - id: dependency_removal
    alias: H09
    risk: medium
    status: implemented
  - id: payload_overflow
    alias: H10
    risk: medium
    status: implemented
  - id: authentication_bypass
    alias: H11
    risk: high
    status: pending
observers:
  - auth_observer
  - authorization_observer
  - audit_observer
  - injection_observer
  - ratelimit_observer
recovery_strategies:
  - restart_service
  - restore_directory
  - purge_artifacts
  - reconnect_client
  - quarantine_endpoint
  - reset_chain
evidence_schema: schemas/security_evidence.yaml
governor_hooks:
  - claim_status_transition
  - operationalization_required
---
