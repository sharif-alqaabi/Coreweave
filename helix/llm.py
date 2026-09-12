"""Thin, provider-agnostic chat call. Swap freely; the architecture is what matters.

TODO: pick a client (anthropic / openai / litellm). Keep the signature.
"""
from __future__ import annotations

from .telemetry import op


@op
def chat(model: str, system: str, user: str, *, json_mode: bool = False, max_tokens: int = 2048) -> str:
    raise NotImplementedError(
        f"llm.chat not wired yet (model={model}). Run loop.py with --dry-run for stub agents."
    )
