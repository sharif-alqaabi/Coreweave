"""Aria — trace miner + patch writer. Evaluates the system, not the science."""
from __future__ import annotations

import json

from helix import llm, telemetry
from helix.kit import Kit
from helix.schema import IterationStats, KitDiff, KitPatch, Lead, PatchKind

from . import prompts


class Aria:
    def __init__(self, model: str, dry_run: bool = False):
        self.model = model
        self.dry_run = dry_run

    @telemetry.op
    def evolve(self, leads: list[Lead], stats: IterationStats, kit: Kit) -> KitDiff:
        if self.dry_run:
            return self._stub(leads, stats)

        verdicts = "\n".join(
            f"- {l.id} [{l.critic.verdict.value} {l.critic.score:.2f}] skills={l.skills_used} reasons={l.critic.reasons}"
            for l in leads if l.critic
        )
        raw = llm.chat(
            model=self.model,
            system=prompts.SYSTEM,
            user=prompts.USER.format(
                iteration=stats.iteration,
                kit_version=kit.version,
                stats_json=stats.model_dump_json(indent=2),
                verdicts=verdicts or "(none)",
                kit=kit.system_prompt_block(),
            ),
            json_mode=True,
        )
        return KitDiff.model_validate({**json.loads(raw), "iteration": stats.iteration})

    def _stub(self, leads: list[Lead], stats: IterationStats) -> KitDiff:
        """Mint one rule + one skill per iteration from the most common kill/park reason."""
        reasons: dict[str, int] = {}
        for l in leads:
            for r in (l.critic.reasons if l.critic else []):
                reasons[r] = reasons.get(r, 0) + 1
        top = max(reasons, key=reasons.get) if reasons else "unspecified"
        n = stats.iteration
        return KitDiff(
            iteration=n,
            summary=f"[stub] most common critic reason: '{top}' ({reasons.get(top, 0)}x)",
            patches=[
                KitPatch(
                    kind=PatchKind.RULE,
                    path=f"rules/{100 + n:03d}_iter{n}_{_slug(top)}.md",
                    content=f"Before proposing a lead, check it against: '{top}'. Leads that trip this are killed.\n",
                    rationale=f"critic named '{top}' {reasons.get(top, 0)} times in iteration {n}",
                    evidence_trace_ids=[l.trace for l in leads if l.critic and top in l.critic.reasons],
                ),
                KitPatch(
                    kind=PatchKind.SKILL,
                    path=f"skills/iter{n}_avoid_{_slug(top)}.md",
                    content=f"# Avoid: {top}\n\nTODO: playbook written by Aria.\n",
                    rationale="stub skill so the loop demonstrates kit mutation",
                ),
            ],
        )


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")[:40]
