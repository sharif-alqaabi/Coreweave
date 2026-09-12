"""JSONL ledger: one object per lead, survivors and corpses alike.

Killed leads are assets. They teach the next kit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from .schema import Lead, Verdict


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, lead: Lead) -> None:
        with self.path.open("a") as f:
            f.write(lead.model_dump_json() + "\n")

    def __iter__(self) -> Iterator[Lead]:
        with self.path.open() as f:
            for line in f:
                if line.strip():
                    yield Lead.model_validate_json(line)

    def survivors(self) -> list[Lead]:
        return [l for l in self if l.survived]

    def killed(self) -> list[Lead]:
        return [l for l in self if l.critic and l.critic.verdict == Verdict.KILL]

    def by_iteration(self, n: int) -> list[Lead]:
        return [l for l in self if l.iteration == n]

    def claims(self) -> list[str]:
        """Prior claims, for novelty / duplicate-kill checks."""
        return [l.claim for l in self]

    def id_allocator(self):
        """Hand out sequential ids within an iteration, before leads are appended."""
        n = sum(1 for _ in self)

        def next_id() -> str:
            nonlocal n
            n += 1
            return f"lead_{n:04d}"

        return next_id
