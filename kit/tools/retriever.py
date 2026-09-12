"""Retrieve raw text / rows from a data shard."""
from __future__ import annotations

from pathlib import Path

NAME = "retriever"
DESCRIPTION = "Return the contents (or first N lines) of a file inside the current data shard."


def run(shard: str, path: str, max_lines: int = 200) -> str:
    p = Path(shard) / path
    if not p.is_file():
        return f"error: {path} not found in shard"
    lines = p.read_text(errors="replace").splitlines()
    return "\n".join(lines[:max_lines])
