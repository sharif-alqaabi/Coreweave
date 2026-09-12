"""Statistical sanity tool (V1 roadmap item): effect size, multiple-testing, leakage checks."""
from __future__ import annotations

NAME = "stats_screen"
DESCRIPTION = "Cheap sanity checks on a reported effect: is q-value present, is n reported, is the effect size non-trivial."


def run(effect_size: float | None = None, p_value: float | None = None, q_value: float | None = None, n: int | None = None) -> dict:
    flags = []
    if q_value is None and p_value is not None:
        flags.append("p-value without multiple-testing correction")
    if q_value is not None and q_value >= 0.05:
        flags.append("q >= 0.05")
    if effect_size is not None and abs(effect_size) < 0.1:
        flags.append("trivial effect size")
    if n is not None and n < 10:
        flags.append("n < 10")
    # TODO: leakage checks (train/test overlap, batch confounds)
    return {"flags": flags, "passes": not flags}
