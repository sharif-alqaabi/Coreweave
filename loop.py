#!/usr/bin/env python3
"""One iteration = scout → critic → aria → swap kit.

    python loop.py --data ./data/shard_01 --iterations 3 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents.aria import Aria
from agents.critic import Critic
from agents.weave_scout import Scout
from helix import telemetry
from helix.config import load_settings
from helix.kit import load_kit, promote, rollback, validate_diff
from helix.ledger import Ledger
from helix.schema import IterationStats, Verdict


def run_iteration(n: int, shard: Path, settings, ledger: Ledger, dry_run: bool) -> IterationStats:
    # 1. Load current kit
    kit = load_kit(settings.kit_dir)
    print(f"\n=== iteration {n} | kit v{kit.version} | rules={len(kit.rules)} skills={len(kit.skills)} tools={kit.tool_names}")

    # 2. Scout
    prior = ledger.claims()
    scout = Scout(settings.scout_model, kit, dry_run=dry_run)
    leads = scout.run(shard, n, prior, ledger.id_allocator())
    print(f"scout proposed {len(leads)} leads")

    # 3. Critic
    critic = Critic(settings.critic_model, dry_run=dry_run)
    for lead in leads:
        lead.critic = critic.judge(lead, prior)
        ledger.append(lead)
        print(f"  {lead.id} → {lead.critic.verdict.value:8s} {lead.critic.score:.2f} {lead.critic.reasons}")

    counts = {v: sum(1 for l in leads if l.critic and l.critic.verdict == v) for v in Verdict}
    stats = IterationStats(
        iteration=n, kit_version=kit.version, proposed=len(leads),
        killed=counts[Verdict.KILL], parked=counts[Verdict.PARK],
        survived=counts[Verdict.SURVIVE], escalated=counts[Verdict.ESCALATE],
        duplicate_kills=sum(1 for l in leads if l.critic and "duplicate of prior lead" in l.critic.reasons),
    )
    print(f"survive-rate {stats.survive_rate:.2f}")

    # 4. Aria
    aria = Aria(settings.aria_model, dry_run=dry_run)
    diff = aria.evolve(leads, stats, kit)
    print(f"aria: {diff.summary} ({len(diff.patches)} patches)")

    # 5. Validate
    problems = validate_diff(diff, kit)
    if problems:
        print("kit diff rejected:", *problems, sep="\n  ")
        return stats

    # 6. Promote
    new_kit = promote(diff, kit)
    for p in diff.patches:
        print(f"  + {p.kind.value}: {p.path}")
    print(f"kit v{kit.version} → v{new_kit.version}")

    (settings.traces_dir / f"iter_{n:03d}.json").write_text(
        json.dumps({"stats": stats.model_dump(), "diff": diff.model_dump()}, indent=2)
    )
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="data shard directory")
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true", help="stub agents; no models, no W&B")
    ap.add_argument("--ledger", type=Path, default=None, help="ledger JSONL (default ledger/leads.jsonl)")
    ap.add_argument("--rollback-threshold", type=float, default=0.0,
                    help="roll kit back if survive-rate drops by more than this between iterations (0 = off)")
    args = ap.parse_args()

    settings = load_settings()
    settings.validate(dry_run=args.dry_run)
    telemetry.init(settings.wandb_project, enabled=not args.dry_run)
    settings.traces_dir.mkdir(exist_ok=True)

    ledger = Ledger(args.ledger or settings.ledger_dir / "leads.jsonl")
    history: list[IterationStats] = []
    for n in range(1, args.iterations + 1):
        stats = run_iteration(n, args.data, settings, ledger, args.dry_run)
        if history and args.rollback_threshold and history[-1].survive_rate - stats.survive_rate > args.rollback_threshold:
            print(f"survive-rate collapsed ({history[-1].survive_rate:.2f} → {stats.survive_rate:.2f}); rolling back kit")
            rollback(load_kit(settings.kit_dir), stats.kit_version)
        history.append(stats)

    print("\n=== summary")
    for s in history:
        print(f"iter {s.iteration}: kit v{s.kit_version} proposed={s.proposed} survived={s.survived + s.escalated} "
              f"killed={s.killed} parked={s.parked} dup_kills={s.duplicate_kills} rate={s.survive_rate:.2f}")


if __name__ == "__main__":
    main()
