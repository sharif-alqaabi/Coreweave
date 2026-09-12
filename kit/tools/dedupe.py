"""Duplicate-lead detector (V1 roadmap item). Placeholder: exact / fuzzy string match."""
from __future__ import annotations

from difflib import SequenceMatcher

NAME = "dedupe"
DESCRIPTION = "Return the closest prior ledger claim and a 0..1 similarity score for a candidate claim."


def run(claim: str, prior_claims: list[str]) -> dict:
    best, score = None, 0.0
    for c in prior_claims:
        s = SequenceMatcher(None, claim.lower(), c.lower()).ratio()
        if s > score:
            best, score = c, s
    # TODO: embeddings instead of SequenceMatcher
    return {"closest": best, "similarity": round(score, 3), "is_duplicate": score > 0.85}
