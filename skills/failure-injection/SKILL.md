---
id: failure-injection
family: hygiene
version: 0.0.1
objective: >
  Actively attempt to break the system through controlled attacks
  and observe whether it fails safely or crashes/reveals data.
inputs:
  - project_root
  - attack_types
actions:
  - enumerate attack surface
  - inject controlled failures
  - observe system response
  - classify findings
experiments:
  - malformed_input
  - invalid_state
  - concurrency_stress
  - duplicated_requests
  - retry_amplification
  - timeout_cascade
  - dependency_failure
  - corrupted_data
  - adversarial_prompts
  - partial_writes
  - race_conditions
evidence_required:
  - attack_results.json
  - system_logs.json
  - recovery_logs.json
success_conditions:
  - system survives or fails safely
  - all failures logged
failure_conditions:
  - crash without recovery
  - data corruption undetected
  - security boundary violated
artifacts:
  - attack_results.json
  - recovery_logs.json
---

# Failure Injection

## PURPOSE
Attack the system to find failure modes.

## EXECUTION
1. Select attack type.
2. Inject failure.
3. Observe: crash, data loss, security bypass, silent error, recovery.
4. Record 13-field evidence.
5. If system survives without detection: CRITICAL finding.

## DOGFOOD RULE
Failure injection must be run against the factory itself before expanding.
