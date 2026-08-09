# Missed Blueprint Stages — Execution Plan

Source: `MASTER_REBUILD_BLUEPRINT.md` sections 26, 27, 29.

We executed the H-series experiments before closing the formal P0–P1 loop.
This document lists the missed stages and the concrete actions required to
retrofit them without redoing work unnecessarily.

---

## What We Already Have (Do Not Rebuild)

| Blueprint Stage | Current Artifact | Status |
|-----------------|------------------|--------|
| Domain model (Claim, Evidence, Experiment, Mutation, Observation, Recovery, Restoration, Status) | `epistemic-hygiene/claim_classifier.py` + 6 modules | Implemented |
| Evidence schema | `artifacts/hygiene/h*.json` + `schemas/evidence.yaml` | Implemented |
| Mutation/observer interfaces | H-series runners (`h03_`, `h05_`, `h06_`, `h07_`, `h09_`, `h10_`) | Implemented ad-hoc |
| Governor | `epistemic-governor/SKILL.md` + `epistemic-hygiene/` | Implemented |
| Factory gate | `factory-meta/SKILL.md` + `factory_gate.json` | Implemented |
| P1 closed-loop experiment | H02–H06 executed, artifacts recorded | Partial — H06 endpoint gap |
| H07/H09/H10 scripts + artifacts | `scripts/hygiene/h*.py` + `artifacts/hygiene/h*.json` | Written, not all passing |

---

## Missed Stages (Must Close Before P2+)

### Gate 1 — Claim can be represented and persisted
**Current gap:** Claims exist only inside runner scripts as string constants.
No central claim registry with `claim_id`, `statement`, `scope`, `current_status`,
`evidence_refs[]`, `last_tested`, `dependencies[]`.

**Action:**
1. Create `core/claims/claim_registry.py` with dataclass `Claim` matching blueprint §5.
2. Add `artifacts/claims/claims.json` as the authoritative store.
3. Update each H-series runner to register its target claims before running.
4. Verify: load all claims from disk, confirm every runner’s target claims exist.

**Effort:** ~2 hours. Unblocks: every downstream gate.

---

### Gate 2 — Mutation can be executed safely
**Current gap:** Mutations are inlined in runner scripts (`rename_directory`,
`inject_tampered_text`, `flood_filesystem`). No `MutationPlugin` interface,
no `preconditions` check, no `risk_level` declaration.

**Action:**
1. Define `MutationPlugin` protocol in `core/mutations/interface.py`.
2. Refactor H06 tampering, H09 dependency removal, H10 disk/payload flood
   into plugin classes implementing the interface.
3. Add `preconditions()` checks (e.g., target endpoint must return 200 before
   tampering).
4. H07: if/when auto-healing is implemented, wrap it as a mutation plugin too.

**Effort:** ~3 hours. Unblocks: Gate 3, P2 sequencer.

---

### Gate 3 — Restoration can be independently verified
**Current gap:** Each runner does its own backup/restore. No centralized
`RestorationVerifier` that takes `state_before` and `state_after` and returns
`(bool, DiffReport)`.

**Action:**
1. Create `core/restoration/verifier.py` with `RestorationVerifier` class.
2. Each runner captures `state_before` via the verifier, not ad-hoc dicts.
3. After restoration, each runner calls `verifier.verify(state_before, state_after)`.
4. H06 endpoint 404: this is a restoration failure — record it as such.

**Effort:** ~2 hours. Unblocks: Gate 4, evidence quality metric.

---

### Gate 4 — Evidence artefact is generated
**Current gap:** Artefacts are generated, but the schema is inconsistent.
H06 has `case2_status`; H07 has `verdict` and `case2_status`; H09/H10 have
different field names. No enforced schema.

**Action:**
1. Define canonical evidence schema in `schemas/evidence.yaml`.
2. Create `core/evidence/builder.py` that enforces the schema.
3. Migrate H02–H06 artifacts to the canonical schema (one-time script).
4. H07/H09/H10 runners must use the builder, not manual dict construction.

**Effort:** ~2 hours. Unblocks: Gate 5, Governor rule enforcement.

---

### Gate 5 — Evidence can change claim status under the Governor
**Current gap:** Governor exists as a skill definition. No code enforces
“no evidence → no elevation.” Status transitions are manual, not programmatic.

**Action:**
1. Create `core/governor/governor.py` with `evaluate(claim, evidence)` method.
2. Encode transition rules: past TESTED requires evidence; contradictory
   evidence forces FALSIFIED; stale evidence invalidates prior elevations.
3. Wire each runner to call `governor.evaluate()` after emitting an artifact.
4. Add unit tests for each transition rule.

**Effort:** ~3 hours. Unblocks: Gate 6, human decision surface.

---

### Gate 6 — Human can independently reproduce the result from artefacts alone
**Current gap:** No standalone reproduction guide. Artefacts are not self-contained
— a human needs the runner code, the target project, and the MSB server running.

**Action:**
1. Create `REPRODUCE.md` template with sections:
   - Prerequisites (Python version, target project, env vars)
   - Exact command to run the runner
   - Expected artifact path and checksum
   - How to read the artifact without running the runner
2. Add `sha256` field to every evidence artifact.
3. Run each H-series experiment and verify REPRODUCE.md accuracy.

**Effort:** ~2 hours. Unblocks: benchmark, external review.

---

### Gate 7 — EAAE can be compared against conventional testing
**Current gap:** No baseline comparison. No metrics collection.

**Action:**
1. Define metrics (see blueprint §24) in `docs/metrics.yaml`.
2. Run matched-effort control: write conventional pytest equivalents for
   H05 (contract validation), H06 (tampering check), H09 (dependency test).
3. Measure: claims challenged, defects found, evidence quality, restoration
   success, effort hours.
4. Write comparison report.

**Effort:** ~4 hours. Unblocks: P2+ justification.

---

## P0–P1 Sequence (Retrofit Order)

```
Week 1:
  Day 1-2: Gate 1 (claim registry) + Gate 4 (canonical evidence schema)
  Day 3:   Gate 3 (RestorationVerifier)
  Day 4-5: Gate 2 (MutationPlugin interface) + refactor H06/H09/H10

Week 2:
  Day 1-2: Gate 5 (Governor code)
  Day 3:   Gate 6 (REPRODUCE.md + artifact checksums)
  Day 4-5: Gate 7 (baseline comparison + metrics)
```

H07 auto-healing implementation fits into **Week 1 Day 4-5** if we decide to
implement a recovery primitive, or stays as a recorded **FAIL** with proposed
mutation plugin if not.

---

## H07/H09/H10 Within the Blueprint

| Experiment | Blueprint Stage | Current State | Required Action |
|------------|----------------|---------------|-----------------|
| H07 | MutationPlugin (auto-heal/recovery) | Script written, verdict FAIL | Either implement recovery primitive or leave as FALSIFIED with evidence |
| H09 | MutationPlugin (dependency subtraction) | Script written, verdict PASS | Refactor into plugin, register claims, emit canonical artifact |
| H10 | MutationPlugin (resource exhaustion) | Script written, verdict FAIL | Refactor into plugin; if `/register` 404 persists, mark UNTESTABLE for that endpoint |

---

## Decision Required

1. **Scope:** Execute all 7 gates retroactively, or only Gates 1–5 before P2?
2. **H07:** Implement custom auto-healing recovery primitive, or record as FALSIFIED and move on?
3. **Priority:** Gates first, or finish H07/H09/H10 canonical refactor first?
