---
id: evidence-verification
family: hygiene
version: 0.0.1
objective: >
  Recursively verify every important claim with command, artifact,
  result, timestamp, and status.
inputs:
  - claims
  - evidence_index
actions:
  - extract claims
  - classify each claim
  - verify with evidence
  - identify unsupported/contradicted claims
experiments:
  - claim_classification
  - evidence_traceability
  - contradiction_detection
evidence_required:
  - claims_classification.json
  - evidence_index.json
success_conditions:
  - all critical claims verified
  - no contradictions
failure_conditions:
  - unsupported critical claim
  - contradictory claims
artifacts:
  - claims_classification.json
  - evidence_index.json
  - unsupported_claims.json
---

# Evidence Verification

## PURPOSE
Verify claims with traceable evidence.

## EXECUTION
1. Extract all claims from README, docs, code.
2. Classify: OBSERVED, TESTED, INFERRED, ASSUMED, UNKNOWN, CONTRADICTED.
3. For TESTED claims: verify command, artifact, result, timestamp exist.
4. Emit evidence index.

## DOGFOOD RULE
Factory claims about itself must be verified before every release.
