---
id: epistemic-governor
family: hygiene
version: 0.0.1
objective: >
  Prevent the system from confusing metaphors, axioms, hypotheses,
  implemented mechanisms, and empirical claims.
inputs:
  - project_path
  - documentation_globs
  - code_comment_globs
actions:
  - scan project inputs
  - classify all claims by epistemic status
  - flag category errors
  - generate operationalization tasks
  - convert unknowns to experiments
  - prevent false status promotion
  - generate epistemic audit
evidence_required:
  - claims_classification.json
  - category_errors.json
  - epistemic_report.md
failure_conditions:
  - any claim misclassified
  - any mixed-status statement unresolved
  - any metaphor treated as fact
artifacts:
  - epistemic_report.md
  - claims_classification.json
  - category_errors.json
---

## Epistemic Governor

### Prime Directive
Never certify a metaphor as engineering truth.
Never promote UNKNOWN to SUPPORTED without evidence.
Always operationalize testable claims.

### Skills Invoked
- epistemic-hygiene
- claim-classifier
- claim-registry
- evidence-mapper
- hypothesis-generator
- experiment-generator
- contradiction-detector
- status-updater

### Audit Outputs
- claims_classification.json: every claim, source, status, confidence
- category_errors.json: contradictions and invalid transitions
- epistemic_report.md: human-readable summary with remaining unknowns
