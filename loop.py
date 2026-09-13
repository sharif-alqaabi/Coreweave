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


def best_rules():
    """The rules version with the best TRAIN score (reason accuracy, then precision). Holdout uses
    this, never the newest untested version. Falls back to latest if no metrics yet."""
    mpath = RESULTS / "metrics.csv"
    if not mpath.exists():
        return latest_rules()
    rows = list(csv.DictReader(open(mpath)))
    best = max(rows, key=lambda r: (float(r["reason_accuracy"] or 0), float(r["kill_precision"] or 0)))
    return f"kit/critic/rules_v{best['rules_version']}.md"


def patch_fixes(critic, table, misses, leads_by_id, new_rules):
    """Re-judge only the missed leads with the candidate rules. Returns how many now match the human label."""
    sub = [leads_by_id[m["hypothesis_id"]] for m in misses]
    verdicts = critic.judge_all(sub, table, new_rules)
    return sum(v["label"] == leads_by_id[v["lead_id"]]["label"] for v in verdicts)


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
    mpath = RESULTS / "metrics.csv"
    rows = [r for r in csv.DictReader(open(mpath))] if mpath.exists() else []
    rows = [r for r in rows if int(r["iteration"]) != n] + [{"iteration": n, "rules_version": n,
            "kill_precision": m["screening/kill_precision"], "false_kill_rate": m["screening/false_kill_rate"],
            "reason_accuracy": m["screening/reason_accuracy"], "misses": len(result["misses"])}]
    rows.sort(key=lambda r: int(r["iteration"]))
    with open(mpath, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
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
    out = f"kit/critic/rules_v{n+1}.md"
    for attempt in range(2):                      # guardrails may reject; retry once with the reason
        if not patch.strip():
            break
        try:
            out = apply_patch(base, patch, change_reason=f"iter {n} misses" + (" (rolled back)" if base != rules else ""),
                              author=author, out_version=n + 1)
            if critic.dry_run or not result["misses"]:
                break
            fixed = patch_fixes(critic, table, result["misses"], {l["id"]: l for l in leads}, out)
            print(f"  patch validation: fixes {fixed}/{len(result['misses'])} of this iteration's misses")
            if fixed > 0:
                break
            Path(out).unlink(); Path(out.replace(".md", ".meta.json")).unlink(missing_ok=True)
            raise ValueError("patch fixes none of the misses it was written for")
        except ValueError as e:
            print(f"  patch rejected ({e}); {'retrying' if attempt == 0 else 'keeping rules unchanged'}")
            patch = propose_patch_claude(result["misses"], base, feedback=f"Your previous patch was rejected: {e}. Fix that.") if attempt == 0 and author == "claude" else ""
    if not Path(out).exists():
        Path(out).write_text(Path(base).read_text()); author = "none"
    print(f"  -> {out} (author={author})")
    return m["screening/kill_precision"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--start", type=int, default=0, help="first iteration number (resume; uses rules_v{start})")
    ap.add_argument("--train", default="data/golden/train.json")
    ap.add_argument("--holdout", action="store_true", help="score the best train-scored rules on data/golden/holdout.json once")
    ap.add_argument("--rules", default=None, help="with --holdout: score this rules file instead of the best one")
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
        rules = args.rules or best_rules(); print(f"holdout with {rules}" + ("" if args.rules else " (best train score)"))
        result = evaluate(critic.judge_all(leads, table, rules), leads)
        print("HOLDOUT", {k: round(v, 3) for k, v in result["metrics"].items() if k.startswith("screening/") and isinstance(v, float)})
        json.dump({"rules": rules, "metrics": result["metrics"], "misses": result["misses"]}, open(RESULTS / "holdout.json", "w"), indent=1)
        log_iteration(99, result, rules, {"critic/model": critic.model, "split": "holdout"}, group="helix-osd104-holdout")
        return
    leads = json.load(open(args.train))
    prev = None
    for n in range(args.start, args.start + args.iterations):
        prev = run_iteration(n, leads, table, critic, args, prev)


if __name__ == "__main__":
    main()
