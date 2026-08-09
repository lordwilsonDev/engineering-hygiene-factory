---
id: engineering-hygiene-factory
objective: >
  Transform software projects into experimentally verified, adversarially tested,
  evidence-backed engineering artifacts. Never declare a project "good" from prose
  alone. Execution success is not goal success. Unknowns remain explicitly unknown.
version: 0.0.1
skills:
  - codebase-archaeology
  - test-hygiene
  - failure-injection
  - evidence-verification
  - release-gate
  - security-hygiene
  - concurrency-hygiene
  - state-hygiene
  - data-hygiene
  - api-hygiene
  - observability-hygiene
  - performance-hygiene
  - resource-exhaustion
  - dependency-hygiene
  - configuration-hygiene
  - migration-hygiene
  - compatibility-hygiene
  - reproducibility
  - documentation-hygiene
  - installation-hygiene
  - rollback-hygiene
  - backup-restore
  - audit-hygiene
  - determinism
  - llm-hygiene
  - agent-autonomy
  - self-healing
  - chaos
  - fuzzing
  - mutation-testing
  - negative-space
  - adversarial-review
  - complexity-reduction
  - test-the-tests
  - scientific-validation
  - human-factors
  - disaster-recovery
  - repair
  - verification
  - epistemic-hygiene
  - epistemic-governor
  - factory-meta
outputs:
  - reports/hygiene_report.md
  - artifacts/hygiene/evidence_*.json
---

## Engineering Hygiene Factory

### Prime Directive
Never declare a project "good" from prose alone.
Execution success is not goal success.
Claims require evidence.
Unknowns remain explicitly unknown.

### Usage
Load this skill when running hygiene experiments.
Invoke individual hygiene skills as needed.
Always record evidence before declaring verdict.

### Running the factory

```bash
# msb-v3 (default project)
MSB_REPO=/Users/lordwilson/msb-v3 python scripts/run_factory.py

# any other project with a hygiene suite
python scripts/run_factory.py --project /path/to/project
```

The factory:

1. runs the project's **real pytest suite** (`pytest tests/ -q`) → `regression_passed`;
2. probes the live server's **x-mcp-secret gate** (`/mcp/tools`: correct secret
   → 200, wrong/missing → 401) → `live_auth_verified`;
3. runs the project's `scripts/hygiene/hygiene_runner.py --all --json`,
   validates every artifact against `schemas/experiment.yaml`, and gates on
   the **weakest member verdict**;
4. writes `factory_gate.json` with a `VERIFICATION` block carrying the raw
   pytest + auth evidence so no green is asserted from prose.

### Per-project suites (`suite.json`)

Any project can declare its OWN experiments in
`<project>/scripts/hygiene/suite.json` (projects without it fall back to the
built-in msb-v3 suite):

```json
{
  "experiments": {
    "s01_template_check": {"skill": "configuration-hygiene",
                           "runner": "s01_template_check_runner.py"}
  },
  "live_auth": false
}
```

- `experiments` maps experiment_id → `{skill, runner}`; keys must match the
  experiment_id values the runners emit, values are the ACTUAL runner
  filenames (reproducibility is checked against them).
- `live_auth: false` opts a **serverless project** (pure CLI engine) out of
  the auth probe — it is recorded as scoped-out in a `notes` field, NOT as
  an unresolved unknown.

### Gate fields

| field | meaning |
|---|---|
| `regression_passed` | the project's pytest suite passed when executed BY the factory |
| `live_auth_verified` | the running server enforced x-mcp-secret (200/401/401) on a real probe |
| `reproducibility_documented` | every experiment's standalone runner file exists |
| `critical_invariants_verified` | audit + state integrity members pass |
| `security_boundaries_tested` | contract-fuzzing member passes |
| `unresolved_unknowns` | anything not proven — empty only when everything has evidence |

`unresolved_unknowns` going EMPTY is the definition of a fully-verified gate.
It contains exactly what lacks evidence, never prose.

### Scheduling (optional)

The msb-v3 repo ships a launchd LaunchAgent that runs the factory daily and
alerts when the gate stops being PASS (see `msb-v3/scripts/factory_gate_daily.sh`
and `com.blackswanlabz.msb-factory-gate.plist`).
