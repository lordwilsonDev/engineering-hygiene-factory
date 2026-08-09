---
id: epistemic-hygiene
family: hygiene
version: 0.0.1
objective: >
  Classify every claim in a project by its epistemic status to prevent
  metaphor contamination and false status promotion.
inputs:
  - project_path
  - documentation_globs
  - code_comment_globs
actions:
  - scan documentation and code for claims
  - classify each claim by epistemic status
  - flag category errors and mixed-status statements
  - convert unknowns into operationalization tasks
  - prevent false promotion of status
  - generate epistemic audit
experiments:
  - claim_classification
  - category_consistency
  - metaphor_contamination
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

## Epistemic Hygiene Layer

### Purpose
Prevent the system from confusing axioms, hypotheses, implemented mechanisms, and empirical claims.

### Prime Directive
Never certify a metaphor as engineering truth.
Never promote UNKNOWN to SUPPORTED without evidence.
Always operationalize testable claims.

### Status Taxonomy
- OBSERVED: directly observed in the system
- IMPLEMENTED: exists in code
- DEFINED: mathematically or specification-defined
- TESTED: experimentally tested
- SUPPORTED: evidence supports it
- HYPOTHESIS: testable proposition
- SPECULATIVE: plausible but insufficient evidence
- METAPHOR: conceptual analogy
- UNKNOWN: insufficient information
- FALSIFIED: evidence contradicts it
- UNTESTABLE: cannot be operationalized

### Usage
Run the epistemic parser against a project to generate
claims_classification.json, category_errors.json, and epistemic_report.md.
