"""W&B Weave is the nervous system. This module degrades to a no-op when
weave is not installed or no API key is set, so the loop still runs in
--dry-run mode.
"""
from __future__ import annotations

import uuid
from functools import wraps
from typing import Callable

_weave = None


def init(project: str, enabled: bool = True) -> bool:
    global _weave
    if not enabled:
        return False
    try:
        import weave  # type: ignore

        weave.init(project)
        _weave = weave
        return True
    except Exception:  # ImportError, auth errors — fall back to no-op
        _weave = None
        return False


def op(fn: Callable) -> Callable:
    """Decorate any scout/critic/aria step. Becomes a weave span when enabled."""
    if _weave is not None:
        return _weave.op()(fn)

    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def new_trace_id(prefix: str = "helix") -> str:
    """Placeholder trace id for dry runs. Real runs should use the weave call id."""
    return f"weave://local/{prefix}/{uuid.uuid4().hex[:12]}"


def feedback(trace_id: str, payload: dict) -> None:
    """Attach critic verdicts / aria notes to the object that produced them."""
    # TODO: weave.get_call(trace_id).feedback.add(...)
    return None
