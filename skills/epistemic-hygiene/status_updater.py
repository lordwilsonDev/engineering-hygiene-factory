"""Status updater: prevent invalid status transitions for the reduced seven-status taxonomy."""
from __future__ import annotations

from epistemic_hygiene.claim_classifier import EpistemicStatus

ALLOWED_TRANSITIONS = {
    EpistemicStatus.ASSERTED: {EpistemicStatus.TESTED, EpistemicStatus.SUPPORTED, EpistemicStatus.UNKNOWN},
    EpistemicStatus.TESTED: {EpistemicStatus.SUPPORTED, EpistemicStatus.VALIDATED, EpistemicStatus.FALSIFIED, EpistemicStatus.UNKNOWN},
    EpistemicStatus.SUPPORTED: {EpistemicStatus.VALIDATED, EpistemicStatus.OBSERVED, EpistemicStatus.FALSIFIED, EpistemicStatus.UNKNOWN},
    EpistemicStatus.VALIDATED: {EpistemicStatus.FALSIFIED, EpistemicStatus.UNKNOWN},
    EpistemicStatus.OBSERVED: {EpistemicStatus.TESTED, EpistemicStatus.SUPPORTED, EpistemicStatus.UNKNOWN},
}


def can_transition(from_status: EpistemicStatus, to_status: EpistemicStatus) -> bool:
    if from_status == to_status:
        return True
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())
