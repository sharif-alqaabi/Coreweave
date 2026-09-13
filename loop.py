#!/usr/bin/env python3
"""Helix loop: judge -> score -> log -> revise rules, on the same leads each iteration.

    python3 loop.py --iterations 4 --dry-run                    # plumbing test, no keys
    python3 loop.py --iterations 4 --wait-for-aria 120          # ARIA writes rules via the MCP server
    python3 loop.py --iterations 4 --patch-dir patches/         # or: apply ARIA patches pasted to files
    python3 loop.py --holdout                                   # final rules on holdout, once

Rules live in kit/critic/rules_v{n}.md. Iteration n judges with v{n} and produces v{n+1}
from patches/iter{n}.md (pasted from ARIA) or, if absent, from the Claude fallback.
Rollback: if precision drops vs. the previous iteration, v{n+1} is built from v{n-1}.
"""
import argparse, csv, glob, json, os
from pathlib import Path
from dotenv import load_dotenv
from helix.critic_payload import Table
from helix.critic import Critic
from helix.evaluate import evaluate
from helix.reflect import apply_patch, propose_patch_claude
from helix.wandb_log import log_iteration

load_dotenv()
RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True)


def latest_rules():
    return sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))[-1]


def run_iteration(n, leads, table, critic, args, prev_precision):
    rules = f"kit/critic/rules_v{n}.md"
    verdicts = critic.judge_all(leads, table, rules)
    result = evaluate(verdicts, leads)
    m = result["metrics"]
    print(f"iter {n} rules_v{n}: kill_precision={m['screening/kill_precision']} "
          f"false_kill_rate={m['screening/false_kill_rate']} reason_acc={m['screening/reason_accuracy']:.2f} "
          f"misses={len(result['misses'])}")
    json.dump({"verdicts": verdicts, "metrics": m, "misses": result["misses"]},
              open(RESULTS / f"iter{n}.json", "w"), indent=1)
    with open(RESULTS / "metrics.csv", "a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0: w.writerow(["iteration", "rules_version", "kill_precision", "false_kill_rate", "reason_accuracy", "misses"])
        w.writerow([n, n, m["screening/kill_precision"], m["screening/false_kill_rate"], m["screening/reason_accuracy"], len(result["misses"])])
    result["metrics"]["screening/eval_complete"] = 1          # the automation trigger signal
    log_iteration(n, result, rules, {"critic/model": critic.model, "critic/dry_run": critic.dry_run,
                                      "architect": "aria" if args.patch_dir else "claude"},
                  prev_rules_path=f"kit/critic/rules_v{n-1}.md" if n else None)
    # ---- revise rules for the next iteration ----
    base = rules
    if prev_precision is not None and (m["screening/kill_precision"] or 0) < prev_precision:
        base = f"kit/critic/rules_v{n-1}.md"; print(f"  precision dropped: rolling back to v{n-1} as base")
    next_rules = Path(f"kit/critic/rules_v{n+1}.md")
    if args.wait_for_aria and not next_rules.exists():      # ARIA writes it via the MCP tool
        import time
        print(f"  waiting up to {args.wait_for_aria}s for ARIA to write {next_rules} ...")
        deadline = time.time() + args.wait_for_aria
        while time.time() < deadline and not next_rules.exists():
            time.sleep(2)
    if next_rules.exists():
        print(f"  -> {next_rules} (author=aria via MCP)"); return m["screening/kill_precision"]
    patch_file = Path(args.patch_dir or "patches") / f"iter{n}.md"
    if patch_file.exists():
        patch, author = patch_file.read_text(), "aria"
    elif args.dry_run:
        print("  dry run, no patch file: copying rules unchanged"); patch, author = "", "none"
    else:
        patch, author = propose_patch_claude(result["misses"], base), "claude"
    if patch.strip():
        out = apply_patch(base, patch, change_reason=f"iter {n} misses", author=author)
    else:
        out = f"kit/critic/rules_v{n+1}.md"; Path(out).write_text(Path(base).read_text())
    print(f"  -> {out} (author={author})")
    return m["screening/kill_precision"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--train", default="data/golden/train.json")
    ap.add_argument("--holdout", action="store_true", help="score latest rules on data/golden/holdout.json once")
    ap.add_argument("--table", default="data/raw/OSD-104_rna_seq_differential_expression.csv")
    ap.add_argument("--patch-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-for-aria", type=int, default=0, metavar="SECONDS",
                    help="after logging, wait this long for ARIA to write the next rules via MCP before falling back")
    args = ap.parse_args()
    table = Table(args.table)
    critic = Critic(dry_run=args.dry_run)
    if args.holdout:
        leads = json.load(open("data/golden/holdout.json"))
        result = evaluate(critic.judge_all(leads, table, latest_rules()), leads)
        print("HOLDOUT", {k: v for k, v in result["metrics"].items() if k.startswith("screening/")})
        json.dump(result["metrics"], open(RESULTS / "holdout.json", "w"), indent=1)
        return
    leads = json.load(open(args.train))
    prev = None
    for n in range(args.iterations):
        prev = run_iteration(n, leads, table, critic, args, prev)


if __name__ == "__main__":
    main()
