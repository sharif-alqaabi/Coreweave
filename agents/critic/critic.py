"""Critic — the shutdown valve. Different model, different prompt, different incentives."""
from __future__ import annotations

import json

from helix import llm, telemetry
from helix.schema import CriticVerdict, Lead, Verdict

from . import prompts


class Critic:
    def __init__(self, model: str, dry_run: bool = False):
        self.model = model
        self.dry_run = dry_run

    @telemetry.op
    def judge(self, lead: Lead, prior_claims: list[str]) -> CriticVerdict:
        if self.dry_run:
            return self._stub(lead, prior_claims)

        raw = llm.chat(
            model=self.model,
            system=prompts.SYSTEM,
            user=prompts.USER.format(
                lead_json=lead.model_dump_json(indent=2, exclude={"critic"}),
                prior_claims="\n".join(f"- {c}" for c in prior_claims) or "(none)",
            ),
            json_mode=True,
        )
        verdict = CriticVerdict.model_validate({**json.loads(raw), "critic_model": self.model})
        telemetry.feedback(lead.trace, verdict.model_dump())
        return verdict

    def _stub(self, lead: Lead, prior_claims: list[str]) -> CriticVerdict:
        if lead.claim in prior_claims:
            return CriticVerdict(verdict=Verdict.KILL, score=0.0, reasons=["duplicate of prior lead"], critic_model="stub")
        if lead.claim.startswith("[stub]"):
            return CriticVerdict(verdict=Verdict.PARK, score=0.3, reasons=["no operational next step"], critic_model="stub")
        return CriticVerdict(verdict=Verdict.SURVIVE, score=0.7, reasons=[], critic_model="stub")
