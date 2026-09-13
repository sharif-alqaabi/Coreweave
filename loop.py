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
from helix.critic_payload import Table, Tables
from helix.critic import Critic
from helix.evaluate import evaluate
from helix.reflect import apply_patch, propose_patch_claude, render_patch
from concurrent.futures import ThreadPoolExecutor
ARCHITECTS = [m for m in os.getenv("ARCHITECT_MODELS", "deepseek-ai/DeepSeek-V3.1,Qwen/Qwen3-235B-A22B-Instruct-2507").split(",") if m]
NOISE = 2 / 30                                      # critic noise ~1 lead; roll back only on a >= 2-lead drop
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


def candidate(model, misses, base, critic, table, leads, tmpdir):
    """One architect proposes a patch; score it on ALL train leads. Returns dict or None."""
    for attempt in range(2):
        try:
            patch = propose_patch_claude(misses, base, model=model)
            text, changed = render_patch(base, patch)
            path = f"{tmpdir}/rules_v{900 + hash(model) % 90}.md"; Path(path).write_text(text)
            r = evaluate(critic.judge_all(leads, table, path), leads)
            return {"model": model, "patch": patch, "sections": changed, "acc": r["metrics"]["screening/reason_accuracy"],
                    "misses": {m["hypothesis_id"] for m in r["misses"]}}
        except ValueError as e:                       # guardrail rejection: one retry with the reason
            if attempt: return None
            misses = misses + [{"hypothesis_id": "feedback", "hypothesis_text": f"previous patch rejected: {e}",
                                "human_reason_code": "-", "critic_reason_code": "-"}]
        except Exception as e:
            print(f"  architect {model} failed: {str(e)[:80]}"); return None


def tournament(misses, base, critic, table, leads, current_acc):
    """All architects propose in parallel; the best candidate that beats current_acc wins."""
    tmp = Path("results/_candidates"); tmp.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(len(ARCHITECTS)) as pool:
        cands = [c for c in pool.map(lambda m: candidate(m, misses, base, critic, table, leads, tmp), ARCHITECTS) if c]
    before = {m["hypothesis_id"] for m in misses}
    for c in sorted(cands, key=lambda c: -c["acc"]):
        print(f"  candidate {c['model'].split('/')[-1]:34} {c['sections']} -> {c['acc']:.2f} "
              f"(fixed {len(before - c['misses'])}, broke {len(c['misses'] - before)})")
    best = max(cands, key=lambda c: c["acc"], default=None)
    return best if best and best["acc"] > current_acc else None


def current_version(path):
    return int(path.split("_v")[1][:-3])


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
                  prev_rules_path=f"kit/critic/rules_v{n-1}.md" if n else None, group=args.group)
    # ---- revise rules for the next iteration ----
    base = rules
    acc = m["screening/reason_accuracy"]
    if prev_precision is not None and acc < prev_precision - NOISE:     # prev_precision carries reason accuracy
        base = f"kit/critic/rules_v{n-1}.md"; print(f"  accuracy dropped ({prev_precision:.2f} -> {acc:.2f}): rolling back to v{n-1} as base")
        acc = prev_precision
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
        best = tournament(result["misses"], base, critic, table, leads, acc)
        patch, author = (best["patch"], best["model"].split("/")[-1]) if best else ("", "none")
        if not best:
            print(f"  no candidate beat {acc:.2f}: keeping rules unchanged")
    out = f"kit/critic/rules_v{n+1}.md"
    if patch.strip():
        try:
            out = apply_patch(base, patch, change_reason=f"iter {n} misses" + (" (rolled back)" if base != rules else ""),
                              author=author, out_version=n + 1)
        except ValueError as e:
            print(f"  patch rejected ({e}); keeping rules unchanged"); author = "none"
    if not Path(out).exists():
        Path(out).write_text(Path(base).read_text())
    print(f"  -> {out} (author={author})")
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--start", type=int, default=0, help="first iteration number (resume; uses rules_v{start})")
    ap.add_argument("--train", default="data/golden/train.json")
    ap.add_argument("--holdout", action="store_true", help="score the best train-scored rules on data/golden/holdout.json once")
    ap.add_argument("--rules", default=None, help="with --holdout: score this rules file instead of the best one")
    ap.add_argument("--table", nargs="+", default=sorted(glob.glob("data/raw/*.csv")), help="one or more DGE csvs")
    ap.add_argument("--patch-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--group", default="helix-osd104", help="W&B run group (use e.g. demo-1 for a live run)")
    ap.add_argument("--wait-for-aria", type=int, default=0, metavar="SECONDS",
                    help="after logging, wait this long for ARIA to write the next rules via MCP before falling back")
    args = ap.parse_args()
    table = Tables(args.table)
    critic = Critic(dry_run=args.dry_run)
    if args.holdout:
        leads = json.load(open("data/golden/holdout.json"))
        rules = args.rules or best_rules(); print(f"holdout with {rules}" + ("" if args.rules else " (best train score)"))
        result = evaluate(critic.judge_all(leads, table, rules), leads)
        print("HOLDOUT", {k: round(v, 3) for k, v in result["metrics"].items() if k.startswith("screening/") and isinstance(v, float)})
        payload = {"rules": rules, "n": len(leads), "metrics": result["metrics"], "misses": result["misses"]}
        json.dump(payload, open(RESULTS / "holdout.json", "w"), indent=1)                       # latest
        json.dump(payload, open(RESULTS / f"holdout_{os.path.basename(rules)[:-3]}.json", "w"), indent=1)   # per version
        log_iteration(99, result, rules, {"critic/model": critic.model, "split": "holdout"}, group=f"{args.group}-holdout")
        return
    leads = json.load(open(args.train))
    prev = None
    for n in range(args.start, args.start + args.iterations):
        prev = run_iteration(n, leads, table, critic, args, prev)


if __name__ == "__main__":
    main()
