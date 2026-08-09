#!/usr/bin/env python3
"""Smoke tests for the 7 epistemic-hygiene modules.

Proves the modules import and run a basic happy path — the punch list
flagged them as existing-but-unverified. The modules cross-import each other
as `epistemic_hygiene.<module>`, but the directory on disk is hyphenated
(`skills/epistemic-hygiene/`), so a plain `import epistemic_hygiene` fails.
This test registers an in-memory package alias pointing at the hyphenated
directory, then imports and exercises every module.

Run:  python tests/test_epistemic_modules.py
Exit: 0 when all 7 modules import and pass their smoke check, 1 otherwise.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = FACTORY_ROOT / "skills" / "epistemic-hygiene"

# --- Register the in-memory package alias so cross-imports resolve ----------
_pkg = types.ModuleType("epistemic_hygiene")
_pkg.__path__ = [str(MODULES_DIR)]  # type: ignore[attr-defined]
sys.modules["epistemic_hygiene"] = _pkg
sys.path.insert(0, str(MODULES_DIR))

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"  ok  {name}")
    except Exception as e:  # noqa: BLE001 - smoke test must report any failure
        FAILURES.append(f"{name}: {e!r}")
        print(f"FAIL {name}: {e!r}")


def smoke_claim_classifier() -> None:
    from epistemic_hygiene.claim_classifier import classify, EpistemicClaim, EpistemicStatus
    assert classify("we tested this and it passed") == EpistemicStatus.OBSERVED
    assert classify("we predict the latency is bounded") == EpistemicStatus.HYPOTHESIS
    assert classify("this claim is a hypothesis to verify") == EpistemicStatus.HYPOTHESIS
    # classifier is keyword-driven; unrelated prose is UNKNOWN, not guessed
    assert classify("the sky appears blue on clear days") == EpistemicStatus.UNKNOWN
    claim = EpistemicClaim(text="x", source="test", status=EpistemicStatus.TESTED, confidence=0.9)
    assert claim.confidence == 0.9


def smoke_claim_registry() -> None:
    from epistemic_hygiene.claim_registry import ClaimRegistry
    from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
    reg = ClaimRegistry()
    reg.add(EpistemicClaim(text="fact claim", source="s", status=EpistemicStatus.UNKNOWN, confidence=0.9))
    assert len(reg.category_errors()) == 1  # unknown claim with high confidence
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        reg.to_json(Path(td) / "claims.json")
    assert True


def smoke_contradiction_detector() -> None:
    from epistemic_hygiene.contradiction_detector import detect_contradictions
    from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
    claims = [
        EpistemicClaim(text="the system always recovers", source="a", status=EpistemicStatus.SUPPORTED, confidence=0.8),
        EpistemicClaim(text="the system never recovers", source="b", status=EpistemicStatus.SUPPORTED, confidence=0.8),
    ]
    assert len(detect_contradictions(claims)) == 1


def smoke_evidence_mapper() -> None:
    from epistemic_hygiene.evidence_mapper import map_evidence
    from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "note.md").write_text("the marker token lives here", encoding="utf-8")
        claim = EpistemicClaim(text="the marker token", source="s", status=EpistemicStatus.SUPPORTED, confidence=0.7)
        mapping = map_evidence([claim], root)
        assert len(mapping["the marker token"]) == 1


def smoke_experiment_generator() -> None:
    from epistemic_hygiene.experiment_generator import generate_experiments
    specs = generate_experiments(["latency stays under 50ms"])
    assert len(specs) == 1
    assert specs[0].metric and specs[0].pass_condition


def smoke_hypothesis_generator() -> None:
    from epistemic_hygiene.hypothesis_generator import generate_hypotheses
    from epistemic_hygiene.claim_classifier import EpistemicClaim, EpistemicStatus
    claims = [EpistemicClaim(text="unknown thing", source="s", status=EpistemicStatus.UNKNOWN, confidence=0.5)]
    out = generate_hypotheses(claims)
    assert len(out) == 1 and out[0].status == EpistemicStatus.HYPOTHESIS


def smoke_status_updater() -> None:
    from epistemic_hygiene.status_updater import can_transition
    from epistemic_hygiene.claim_classifier import EpistemicStatus
    assert can_transition(EpistemicStatus.UNKNOWN, EpistemicStatus.HYPOTHESIS)
    assert not can_transition(EpistemicStatus.UNKNOWN, EpistemicStatus.FALSIFIED)  # illegal jump


def main() -> int:
    print(f"Epistemic-hygiene module smoke tests ({len(list(MODULES_DIR.glob('*.py')))} files in {MODULES_DIR})")
    check("claim_classifier", smoke_claim_classifier)
    check("claim_registry", smoke_claim_registry)
    check("contradiction_detector", smoke_contradiction_detector)
    check("evidence_mapper", smoke_evidence_mapper)
    check("experiment_generator", smoke_experiment_generator)
    check("hypothesis_generator", smoke_hypothesis_generator)
    check("status_updater", smoke_status_updater)
    print(f"\n{'ALL PASS' if not FAILURES else f'{len(FAILURES)} FAILURES'}")
    for f in FAILURES:
        print(f"  - {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
