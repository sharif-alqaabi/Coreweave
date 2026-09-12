"""Tool registry. Aria may add modules here; each exposes `NAME`, `DESCRIPTION`, and `run(**kwargs)`.

The scout sees `NAME`/`DESCRIPTION`; the loop dispatches to `run`.
"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def load_tools() -> dict[str, ModuleType]:
    import kit.tools as pkg

    tools: dict[str, ModuleType] = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name in ("registry",) or info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"kit.tools.{info.name}")
        if hasattr(mod, "run") and hasattr(mod, "NAME"):
            tools[mod.NAME] = mod
    return tools
