"""Weave — scout + telemetry.

Reads a data shard, proposes leads, and writes a full trace for every claim.
"""
from __future__ import annotations

import json
from pathlib import Path

from helix import llm, telemetry
from helix.kit import Kit
from helix.schema import Evidence, Lead

from . import prompts


class Scout:
    def __init__(self, model: str, kit: Kit, dry_run: bool = False, max_leads: int = 5):
        self.model = model
        self.kit = kit
        self.dry_run = dry_run
        self.max_leads = max_leads

    @telemetry.op
    def run(self, shard: Path, iteration: int, prior_claims: list[str], next_id) -> list[Lead]:
        if self.dry_run:
            return self._stub(shard, iteration, next_id)

        raw = llm.chat(
            model=self.model,
            system=prompts.SYSTEM.format(kit=self.kit.system_prompt_block()),
            user=prompts.USER.format(
                shard_name=shard.name,
                shard_summary=self._summarize_shard(shard),
                prior_claims="\n".join(f"- {c}" for c in prior_claims) or "(none)",
                max_leads=self.max_leads,
            ),
            json_mode=True,
        )
        leads: list[Lead] = []
        for item in json.loads(raw):
            item.update(id=next_id(), iteration=iteration, trace=telemetry.new_trace_id("scout"))
            leads.append(Lead.model_validate(item))
        return leads

    def _summarize_shard(self, shard: Path) -> str:
        """TODO: real retrieval — parse CSV/TSV headers, paper abstracts, figure captions.
        Tools in kit/tools/ should do the heavy lifting; this is the fallback."""
        files = sorted(p for p in shard.rglob("*") if p.is_file())
        return "\n".join(f"- {p.relative_to(shard)} ({p.stat().st_size} bytes)" for p in files) or "(empty shard)"

    def _stub(self, shard: Path, iteration: int, next_id) -> list[Lead]:
        """Placeholder leads so the loop runs end-to-end without models."""
        return [
            Lead(
                id=next_id(),
                iteration=iteration,
                claim=f"[stub] something interesting in {shard.name} (lead {i})",
                evidence=[Evidence(source=f"file:{shard.name}/example.csv", artifact="table", rows=[f"row_{i}"])],
                confidence=0.5,
                why_not_known="stub",
                next_step="stub",
                skills_used=list(self.kit.skills)[:1],
                trace=telemetry.new_trace_id("scout"),
            )
            for i in range(2)
        ]
