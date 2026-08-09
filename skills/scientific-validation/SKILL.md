---
id: scientific-validation
family: hygiene
version: 0.0.1
objective: >
  Verify claims using scientific method: hypothesis, experiment,
  observation, conclusion. No claim without reproducible experiment.
inputs:
  - project_root
  - claims
actions:
  - formalize hypotheses
  - design experiments
  - run experiments
  - draw conclusions
experiments:
  - hypothesis_test
  - reproducibility_check
  - statistical_validation
evidence_required:
  - hypotheses.yaml
  - experiment_results.json
  - conclusions.yaml
success_conditions:
  - all hypotheses tested
  - conclusions supported by data
failure_conditions:
  - untested hypothesis
  - conclusion without evidence
artifacts:
  - hypotheses.yaml
  - experiment_results.json
---

# Scientific Validation

## PURPOSE
Apply scientific method to engineering claims.
