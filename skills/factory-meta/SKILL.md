---
id: factory-meta
family: hygiene
version: 0.0.1
objective: >
  Orchestrate the engineering-hygiene-factory: select which hygiene skills to
  run for a given project, sequence them, aggregate their evidence, and gate the
  final verdict. The root manifest (../../SKILL.md) declares the factory and its
  members; this meta-skill is the runnable control loop over them.
inputs:
  - project_path
  - target_skills        # subset of member skills, or "all"
  - evidence_dir         # where experiment artifacts are written
actions:
  - resolve target hygiene skills from the factory manifest
  - order skills (archaeology/inventory first, gates last)
  - run each skill's experiment and collect its evidence artifact
  - refuse to promote any verdict without a recorded artifact
  - aggregate per-skill verdicts into a factory-level report
  - hand unresolved unknowns to epistemic-governor
evidence_required:
  - reports/hygiene_report.md
  - artifacts/hygiene/*.json
failure_conditions:
  - any target skill run without a recorded evidence artifact
  - any factory-level "pass" while a member verdict is fail/unknown
  - any claim of coverage for a skill that was skipped
artifacts:
  - reports/hygiene_report.md
  - artifacts/hygiene/factory_gate.json
---

## Factory Meta

### Prime Directive
The factory never declares a project "good" from prose alone.
A factory-level pass requires an evidence artifact for every skill it claims to
have run — no artifact, no coverage. Execution success is not goal success.

### Relationship to the manifest
- `../../SKILL.md` is the **factory manifest**: identity, objective, and the list
  of member hygiene skills.
- `factory-meta` (this skill) is the **control loop**: it reads that manifest,
  chooses and orders skills, runs them, and aggregates their verdicts.

### Orchestration order
1. Inventory / archaeology skills (`codebase-archaeology`, `dependency-hygiene`).
2. Per-domain hygiene skills (state, data, api, concurrency, observability, ...).
3. Adversarial skills (`failure-injection`, `chaos`, `fuzzing`, `mutation-testing`).
4. Epistemic pass (`epistemic-governor`) to resolve claim/status mismatches.
5. Gates last (`release-gate`, `verification`) — these read the aggregated evidence.

### Aggregation rule
`factory_gate.json` records, per member skill: verdict, severity, and the path to
its evidence artifact. The factory verdict is the **weakest** member verdict:
any `fail` ⇒ factory `fail`; any `unknown` ⇒ factory `blocked`; only all-`pass`
(or explicitly-waived) ⇒ factory `pass`.

### Usage
Load this skill to run the factory end-to-end or over a chosen subset. Invoke
individual hygiene skills directly for single-experiment work; use `factory-meta`
when you need the aggregated, gated verdict across many.
