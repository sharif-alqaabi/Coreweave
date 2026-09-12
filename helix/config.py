"""Environment-driven settings.

Scout, critic, and architect MUST be different models. That is the whole
point (see README "Why the three-way split").
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    scout_model: str = field(default_factory=lambda: os.getenv("SCOUT_MODEL", ""))
    critic_model: str = field(default_factory=lambda: os.getenv("CRITIC_MODEL", ""))
    aria_model: str = field(default_factory=lambda: os.getenv("ARIA_MODEL", ""))

    wandb_project: str = field(default_factory=lambda: os.getenv("WANDB_PROJECT", "helix"))
    wandb_api_key: str = field(default_factory=lambda: os.getenv("WANDB_API_KEY", ""))

    kit_dir: Path = ROOT / "kit"
    ledger_dir: Path = ROOT / "ledger"
    traces_dir: Path = ROOT / "traces"

    def validate(self, dry_run: bool = False) -> None:
        if dry_run:
            return
        missing = [n for n, v in (("SCOUT_MODEL", self.scout_model),
                                  ("CRITIC_MODEL", self.critic_model),
                                  ("ARIA_MODEL", self.aria_model)) if not v]
        if missing:
            raise SystemExit(f"missing env: {', '.join(missing)} (or pass --dry-run)")
        if self.scout_model == self.critic_model:
            raise SystemExit("SCOUT_MODEL and CRITIC_MODEL must differ — generation and judgment never share a brain.")


def load_settings() -> Settings:
    return Settings()
