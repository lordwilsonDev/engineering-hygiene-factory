---
id: mutation-testing
family: hygiene
version: 0.0.1
objective: >
  Verify test suite catches seeded faults. Mutation score indicates
  test effectiveness.
inputs:
  - project_root
  - source_files
  - test_command
actions:
  - generate mutants
  - run tests against mutants
  - calculate mutation score
experiments:
  - mutation_generation
  - mutant_killing
  - mutation_score
evidence_required:
  - mutation_results.json
  - surviving_mutants.json
success_conditions:
  - mutation score above threshold
  - no surviving critical mutants
failure_conditions:
  - low mutation score
  - surviving critical mutants
artifacts:
  - mutation_results.json
  - surviving_mutants.json
---

# Mutation Testing

## PURPOSE
Verify test effectiveness via mutation.
