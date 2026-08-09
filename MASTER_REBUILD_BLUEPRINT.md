**MASTER REBUILD BLUEPRINT**  
**Epistemically Accountable Adversarial Experiment (EAAE)**  
Engineering Hygiene Factory — Rebuilt from First Principles

---

## 1. Executive Architecture

The system is a minimal research-and-engineering platform whose sole purpose is to execute Epistemically Accountable Adversarial Experiments against a concrete software target. Each experiment captures state, applies a controlled adversarial mutation, observes behaviour, restores the target, verifies restoration, emits an immutable evidence artefact, and proposes a status transition for one or more claims. An Epistemic Governor enforces that no claim may rise in epistemic strength without such evidence. The primary output is a human decision surface that makes residual uncertainty explicit. External primitives (claim models, property-based testing, hash-chained audit, skill packaging) are adopted or thinly wrapped; only the binding of local restorable mutation to evidence-obligated status change is treated as native.

---

## 2. Fundamental Problem

Software projects accumulate claims about their own behaviour, reliability, and correctness that are frequently treated as established knowledge without having been subjected to systematic adversarial challenge under controlled, restorable conditions. Conventional testing answers "did this case pass?"; it does not answer "what do we actually know, and how reliable is that knowledge?"

---

## 3. Central Primitive

**Epistemically Accountable Adversarial Experiment (EAAE)**

A controlled experiment against a concrete software system that executes the following sequence under strict guarantees:

```
CLAIM
  → PRECONDITION / STATE CAPTURE
  → ADVERSARIAL MUTATION
  → OBSERVATION
  → RECOVERY (functional restoration of service behaviour)
  → RESTORATION (return of experiment environment to pre-experiment state)
  → POST-CONDITION VERIFICATION
  → EVIDENCE ARTEFACT
  → EPISTEMIC STATUS TRANSITION (governed)
  → HUMAN / POLICY DECISION
```

Defining constraint: a claim cannot acquire stronger epistemic status merely because a test passed; it must acquire appropriate evidence produced by a controlled experiment. The experiment must not leave the target in an undefined state.

---

## 4. System Invariants

1. State is captured before any mutation.
2. Mutation occurs inside a declared isolation boundary.
3. Restoration is attempted regardless of experiment outcome (`finally`-equivalent semantics).
4. Post-restoration state is independently verified against the captured pre-state.
5. Failed restoration is recorded as evidence and treated as an unresolved incident.
6. No experiment may silently modify state outside its declared scope.
7. No evidence artefact → no status elevation.
8. Contradictory evidence is never discarded silently.
9. Every status transition is attributable to one or more evidence artefacts and a governor decision.
10. Evidence artefacts are immutable once written.

---

## 5. Domain Model

**Claim**  
- `claim_id`, `statement` (atomic propositions), `scope` / epistemic boundary, `origin`, `current_status`, `confidence`, `evidence_refs[]`, `last_tested`, `dependencies[]`

**Evidence Artefact**  
- Immutable JSON record linking experiment, claim(s), states, mutation, observation, recovery, restoration result, verdict, and proposed transitions.

**Experiment**  
- Definition of target claims, mutation, observer, recovery strategy, isolation level, timeouts, and resource bounds.

**Mutation**  
- Plugin with `mutation_id`, preconditions, action, expected failure mode, observation strategy, recovery strategy, risk level.

**Observation**  
- Machine-readable capture of actual versus expected behaviour (HTTP, process, filesystem, logs, metrics, exit codes).

**Recovery**  
- Attempt to return the *service* to a functioning state (reconnect, restart, respawn, quarantine).

**Restoration**  
- Return of the *experiment environment* to the verified pre-experiment state.

**Status**  
- Graded epistemic value enforced by the Governor.

---

## 6. Architecture

```
External Primitives
  (Belief/Stress/Recovery model, Hypothesis, hash-chain audit, skill format)
        ↓
Integration Adapters
  (status mapper, recovery extension, restore library, strategy compiler, skill loader, audit wrapper)
        ↓
Core EAAE Runtime
  Experiment Runner → Mutation Engine → Observer → Recovery Engine → Restoration Verifier
        ↓
Evidence Store + Audit Chain
        ↓
Epistemic Governor + Claim Registry
        ↓
Factory Gate
        ↓
Human Decision Surface (factory_gate.json + hygiene_report.md)
```

Data flows strictly downward; status elevation can occur only through the Governor after evidence is accepted.

---

## 7. Interfaces (Public Contracts)

**ExperimentRunner**  
```text
run(claim_ids, target, mutation, observer, recovery, isolation) → EvidenceArtefact
```

**MutationPlugin**  
```text
preconditions(target) → bool
apply(target) → MutationResult
```

**Observer**  
```text
observe(target, expected) → ObservationRecord
```

**RecoveryStrategy**  
```text
recover(target, failure_context) → RecoveryResult
```

**RestorationVerifier**  
```text
verify(state_before, state_after) → (bool, DiffReport)
```

**EpistemicGovernor**  
```text
evaluate(claim, evidence) → TransitionDecision
```

**FactoryGate**  
```text
decide(claims, evidence_history, policy) → GateVerdict
```

All interfaces are narrow, replaceable, and independently testable.

---

## 8. Evidence Model

Mandatory fields:

```text
experiment_id, claim_ids[], timestamp, target, runner_version, environment,
state_before, mutation, observation, expected_result, actual_result,
recovery_action, state_after, restoration_verified, verdict, confidence,
errors[], proposed_status_transitions[]
```

Artefacts are written once to a deterministic filesystem layout:

```
artifacts/hygiene/<experiment_id>_<timestamp>.json
```

Integrity is provided by an optional hash-chain (OrgKernel-style adapter). Retention and compaction are deferred until the minimum system is validated.

---

## 9. Epistemic Model

Retained and refined 11-status taxonomy (evaluated for necessity):

| Status        | Meaning                                      | Entry requires evidence? |
|---------------|----------------------------------------------|---------------------------|
| UNKNOWN       | No claim yet formed                          | —                         |
| METAPHOR      | Non-literal or rhetorical language           | —                         |
| SPECULATIVE   | Unsupported conjecture                       | —                         |
| HYPOTHESIS    | Testable but untested statement              | —                         |
| DEFINED       | Explicitly stated with boundary              | Optional                  |
| IMPLEMENTED   | Code exists that purports to realise it      | Optional                  |
| OBSERVED      | Behaviour seen under non-adversarial conditions | Optional               |
| TESTED        | Subjected to at least one controlled experiment | **Yes**                |
| SUPPORTED     | Multiple consistent experiments              | **Yes**                   |
| FALSIFIED     | Contradicted by evidence                     | **Yes**                   |
| UNTESTABLE    | Declared outside experimental reach          | Explicit declaration      |

**Transition rules (Governor)**  
- Elevation past TESTED requires one or more valid evidence artefacts.  
- Contradictory evidence forces CHALLENGED or FALSIFIED.  
- Stale evidence (target changed materially) invalidates prior elevations.  
- Human approval may be required for high-severity transitions.  
- No silent upgrades.

---

## 10. Experiment Lifecycle

```
1. Load claim(s) and experiment definition
2. Capture state_before (files, processes, ports, config, env)
3. Verify preconditions
4. Apply mutation inside isolation boundary
5. Execute observation probes
6. Attempt recovery (service-level)
7. Attempt restoration (environment-level) — always, in finally
8. Run RestorationVerifier
9. Emit EvidenceArtefact (including restoration_verified)
10. Submit to Governor for status decision
11. Record Gate verdict
12. Produce human report fragment
```

Any failure at steps 7–8 marks the experiment as an unresolved incident.

---

## 11. Isolation Model

Progressive levels (implement only what is required):

- **Level 1** (minimum for first experiment): temporary workspace + explicit backup/restore of declared paths.  
- Level 2: copy-on-write project snapshot.  
- Level 3: process isolation.  
- Level 4: container.  
- Level 5: sandbox/VM.

First experiment uses Level 1. Escape or incomplete restoration is treated as experiment failure.

---

## 12. Mutation System

Plugin architecture. Each mutation declares:

```text
mutation_id, target, preconditions, action, expected_failure,
observation_strategy, recovery_strategy, risk_level
```

Initial set (mapped to prior H-series):

- Contract / schema violation (Hypothesis-backed)
- Process termination / disconnect
- Dependency subtraction
- Resource exhaustion / oversized payload
- Audit-chain tampering
- Idempotent replay
- Controlled restart

Mutations are never hard-coded into the runner.

---

## 13. Observation System

Independent of mutation where practical. Captures:

- HTTP status, body, headers
- Process existence and exit codes
- Filesystem diffs
- Log excerpts
- Metrics / resource counters
- Structured application events

Produces machine-readable `ObservationRecord` comparing expected versus actual.

---

## 14. Recovery + Restoration

**Recovery** (service behaviour): reconnect, restart, respawn, quarantine, alert.  
**Restoration** (experiment environment): restore files, processes, configuration, temporary resources to verified pre-state.

They are separate operations. Both are recorded. Failed restoration elevates the incident severity.

---

## 15. Audit

Thin adapter over a hash-chained, independently verifiable log (OrgKernel-style or equivalent).  
Interface:

```text
append(entry) → hash
verify(chain_id) → bool
```

The system must remain functional if the audit backend is replaced. Evidence artefacts themselves remain the primary provenance.

---

## 16. Factory Gate

Decision function returning one of:

- PASS  
- FAIL  
- INCONCLUSIVE  
- BLOCKED  
- RESTORATION_FAILURE  
- HUMAN_REVIEW_REQUIRED  

Never reduced to a boolean. Incorporates claim status, evidence quality, restoration result, and policy.

---

## 17. Human Decision Surface

`hygiene_report.md` + `factory_gate.json` must answer:

- What did we believe?  
- What did we test?  
- How did we attack it?  
- What happened?  
- What evidence was produced?  
- Was the system restored?  
- What changed in our knowledge?  
- What remains uncertain?  
- What should we do next?

---

## 18. Security Model

Trust boundaries:  
- Target code is untrusted.  
- Mutation plugins run with least privilege.  
- Evidence store is append-only / integrity-protected.  
- Secrets never appear in artefacts.  
- Resource bounds prevent exhaustion attacks by the experiments themselves.

Threats explicitly modelled: mutation escape, privilege escalation, artefact tampering, evidence forgery, secret leakage, process escape, rollback failure.

---

## 19. Testing Strategy

- Unit: each primitive in isolation.  
- Contract: interface and schema conformance.  
- Property-based: Hypothesis on mutation and governor rules.  
- Integration: full lifecycle with mocked target.  
- Restoration: before/after equivalence suites.  
- Adversarial: deliberate restoration and observation failures.  
- End-to-end: claim → experiment → evidence → status → report.  
- Regression: previously discovered failure modes.

---

## 20. Repository Structure

```text
core/
  claims/
  evidence/
  governor/
  runner/
experiments/
mutations/
observers/
recovery/
restoration/
audit/
sequencer/
gates/
reporting/
integrations/
  hypothesis/
  audit_chain/
  skill_loader/
tests/
artifacts/
docs/
```

Each package declares responsibility, public interface, dependencies, and invariants.

---

## 21. Dependency Strategy

| Component                    | Classification          | Action                          |
|-----------------------------|-------------------------|---------------------------------|
| Specsmith-style belief model| OPTIONAL ADAPTER        | Thin wrap or reimplement minimal subset |
| OrgKernel-style audit chain | OPTIONAL ADAPTER        | Interface + replaceable backend |
| Hypothesis                  | CORE (for contract experiments) | Direct use                     |
| Chaos Toolkit               | REFERENCE               | Learn schema patterns only      |
| Anthropic Skills format     | OPTIONAL ADAPTER        | Loader compatibility            |
| Shared backup/restore        | CUSTOM                  | Native library                  |
| EAAE runner + governor      | CUSTOM                  | Native                          |

No external package becomes part of the project’s identity.

---

## 22. Minimum Viable Research System

```
One Claim
  → One Mutation (API contract adversarial test)
  → One Observer
  → Level-1 Isolation + Restore
  → Evidence Artefact
  → Governor status transition
  → Decision Report
```

This is the smallest system capable of testing the central thesis. Nothing else is built until this loop is closed and measured.

---

## 23. Benchmark

**Control**: conventional test suite of matched engineering effort (unit + property-based + manual adversarial cases).  
**Treatment**: EAAE sequence of matched effort.

Same target service, same time budget, same reviewers.

---

## 24. Metrics

- Claims challenged  
- Claims falsified or demoted  
- False-confidence reduction (pre/post status distribution)  
- Defects newly discovered  
- Evidence quality score (completeness + restoration success)  
- Restoration failure rate  
- Residual unrepaired state  
- Independent reviewer agreement on status changes  
- Engineering effort (person-hours)  
- Wall-clock and compute cost  

All metrics defined before the comparative run.

---

## 25. Falsification Criteria

The hypothesis is rejected if, under matched effort:

- EAAE produces no material improvement in claim falsification or false-confidence reduction,  
- restoration is unreliable,  
- reviewers cannot agree on status changes,  
- evidence quality is not superior,  
- or operational cost outweighs informational benefit.

Any component that fails its kill condition is simplified, redesigned, or removed.

---

## 26. Implementation Roadmap

**P0 — Foundation**  
Domain model, evidence schema, runner interface, state capture, mutation/observer interfaces, restoration verifier, claim/status model, governor, minimal gate.

**P1 — First Closed Loop**  
One real experiment (contract adversarial), baseline comparison harness, evidence reporting, audit adapter, recovery engine.

**P2 — Expansion**  
Deterministic sequencer, additional mutations, skill discovery, cross-experiment evidence channel.

**P3 — Research & Scale**  
Adaptive selection, richer epistemic reasoning, external integrations, distributed execution (only after P0–P2 validated).

---

## 27. Validation Gates

1. Claim can be represented and persisted.  
2. Mutation can be executed safely.  
3. Restoration can be independently verified.  
4. Evidence artefact is generated.  
5. Evidence can change claim status under the Governor.  
6. Human can independently reproduce the result from artefacts alone.  
7. EAAE can be compared against conventional testing on defined metrics.

No phase advances without its gate.

---

## 28. Failure Forecast

| Failure                    | Detection                     | Prevention                     | Recovery                      | Test |
|---------------------------|-------------------------------|--------------------------------|-------------------------------|------|
| Restoration gap           | Verifier mismatch             | Explicit state capture         | Incident + manual restore     | Yes  |
| State leakage             | Post-experiment audit         | Isolation levels               | Quarantine                    | Yes  |
| False epistemic elevation | Governor rule violation       | Mandatory evidence             | Status rollback               | Yes  |
| Evidence corruption       | Hash-chain / checksum         | Append-only store              | Reject artefact               | Yes  |
| Nondeterminism            | Repeated runs                 | Seeded mutations, frozen env   | Mark inconclusive             | Yes  |
| Taxonomy inflation        | Status usage metrics          | Periodic necessity review      | Collapse statuses             | —    |
| Mutation escape           | Process/file monitoring       | Least privilege, Level ≥ 3     | Kill + incident               | Yes  |
| Confirmation bias         | Blinded reviewer protocol     | Pre-registered metrics         | Independent replication       | Yes  |

---

## 29. Rebuild-from-Zero Plan

1. Write evidence schema and claim model.  
2. Implement ExperimentRunner skeleton with `finally` restoration.  
3. Implement Level-1 state capture + RestorationVerifier.  
4. Implement one MutationPlugin + one Observer.  
5. Implement Governor with "no evidence → no elevation" rule.  
6. Close the loop: claim → experiment → evidence → status → report.  
7. Instrument metrics and run baseline comparison.  
8. Only after gate 7 passes, introduce adapters and additional experiments.

---

## 30. Final Architectural Judgment

After removing everything the ecosystem already provides, the only element worth building is the **Epistemically Accountable Adversarial Experiment** itself: the enforced binding of local, restorable adversarial mutation to evidence that is allowed to change graded epistemic status, together with the human decision surface that refuses to collapse uncertainty into a pass/fail bit.

Everything else—claim ontologies, stress operators, hash chains, property-based generators, skill loaders—is scaffolding that should be borrowed or thinly adapted. The project deserves to exist only for as long as that central primitive demonstrably improves what is known about a software system beyond what conventional testing of equivalent effort already achieves.
