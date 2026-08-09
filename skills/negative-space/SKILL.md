---
id: negative-space
family: hygiene
version: 0.0.1
objective: >
  Verify the system does NOT do things it shouldn't: no silent data
  loss, no unauthorized mutations, no hidden state changes.
inputs:
  - project_root
  - invariants
actions:
  - enumerate negative invariants
  - test absence of behavior
  - verify no silent failures
experiments:
  - silent_data_loss_detection
  - unauthorized_mutation_detection
  - hidden_state_change_detection
  - absence_proof
evidence_required:
  - negative_results.json
  - invariant_proofs.json
success_conditions:
  - all negative invariants hold
  - no silent failures
failure_conditions:
  - silent data loss
  - unauthorized mutation
  - hidden state change
artifacts:
  - negative_results.json
  - invariant_proofs.json
---

# Negative Space

## PURPOSE
Verify absence of unwanted behavior.
