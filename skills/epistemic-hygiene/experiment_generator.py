"""Experiment generator: turn hypotheses into executable experiment specs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ExperimentSpec:
    hypothesis: str
    procedure: str
    metric: str
    baseline: str
    pass_condition: str
    fail_condition: str


def generate_experiments(hypotheses: List[str]) -> List[ExperimentSpec]:
    specs: List[ExperimentSpec] = []
    for h in hypotheses:
        specs.append(
            ExperimentSpec(
                hypothesis=h,
                procedure="Implement controlled comparison under stated conditions.",
                metric="Define one primary measurable outcome.",
                baseline="Use current system behavior or accepted threshold.",
                pass_condition="Statistically significant improvement or equivalence.",
                fail_condition="No measurable effect or regression beyond tolerance.",
            )
        )
    return specs
