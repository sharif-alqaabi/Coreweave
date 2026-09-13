"""The product path: dataset CSV in, judged leads out. No labels needed.

    from helix.product import run_pipeline
    out = run_pipeline("data/raw/OSD-421_differential_expression.csv")   # ~90 s
    out["survivors"], out["killed"], out["summary"], out["rules"]

Steps: summarize (pandas) -> generate leads (scout LLM) -> enrich with true numbers (pandas)
-> judge every lead with the trained rules (critic LLM). Used by the marimo app and the CLI.
"""
import csv, glob, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from helix.summarize import summarize
from helix.critic_payload import Table, enrich
from helix.critic import Critic
from helix import llm

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = {"id", "shape", "claim", "rows", "why_not_known", "next_step"}


def best_rules():
    """Rules the product ships: best HOLDOUT reason accuracy (results/holdout_rules_v*.json), because the
    loop promotes by train score and that overfits (v4: train 0.84 but holdout 0.64; v2: 0.81 / 0.73).
    Falls back to best train score, then to the newest version."""
    versions = sorted(glob.glob(os.path.join(ROOT, "kit/critic/rules_v*.md")), key=lambda p: int(p.split("_v")[1][:-3]))
    holdout = glob.glob(os.path.join(ROOT, "results", "holdout_rules_v*.json"))
    if holdout:
        score = lambda f: json.load(open(f))["metrics"]["screening/reason_accuracy"] or 0
        best = max(holdout, key=score)
        return os.path.join(ROOT, f"kit/critic/rules_v{best.split('_v')[-1][:-5]}.md")
    mpath = os.path.join(ROOT, "results", "metrics.csv")
    if os.path.exists(mpath):
        rows = list(csv.DictReader(open(mpath)))
        best = max(rows, key=lambda r: (float(r["reason_accuracy"] or 0), float(r["kill_precision"] or 0)))
        return os.path.join(ROOT, f"kit/critic/rules_v{best['rules_version']}.md")
    return versions[-1]


def generate(summary_text, dataset, n=60, prompt_path=None):
    prompt = open(prompt_path or os.path.join(ROOT, "agents/weave_scout/scout_prompt_60.md")).read()
    if n != 60:
        prompt = prompt.replace("Produce 60 leads", f"Produce {n} leads").replace("lead_001 through lead_060", f"lead_001 through lead_{n:03d}")
    text = llm.chat("You output only a JSON array.", prompt + "\n" + summary_text, max_tokens=12000)
    m = re.search(r"\[.*\]", text, re.S)
    leads = [l for l in (json.loads(m.group()) if m else []) if REQUIRED <= set(l)]
    for i, l in enumerate(leads, 1):
        l["id"] = f"{dataset}_lead_{i:03d}"; l["dataset"] = dataset
    return leads


def run_naive(csv_path, n_leads=60):
    """The baseline for the demo: scout only. No numbers attached, no critic, every lead is a 'finding'."""
    dataset = os.path.basename(csv_path).split("_")[0]
    summary = summarize(csv_path)
    return {"dataset": dataset, "summary": summary, "leads": generate(summary, dataset, n_leads)}


def judge_leads(leads, csv_path, rules_path=None):
    """Attach the real numbers and run the critic on leads that already exist (the reveal after run_naive)."""
    table = Table(csv_path); enrich(leads, table)
    rules = rules_path or best_rules()
    verdicts = Critic().judge_all(leads, table, rules)
    by_id = {l["id"]: l for l in leads}
    judged = [{**by_id[v["lead_id"]], "label": v["label"], "confidence": v["confidence"], "reason": v["reason"]} for v in verdicts]
    return {"rules": rules, "survivors": [j for j in judged if j["label"] == "ok"], "killed": [j for j in judged if j["label"] != "ok"]}


def run_pipeline(csv_path, rules_path=None, n_leads=60, progress=print):
    t0 = time.time()
    dataset = os.path.basename(csv_path).split("_")[0]
    progress("summarizing"); summary = summarize(csv_path)
    progress("generating leads"); leads = generate(summary, dataset, n_leads)
    progress("attaching true numbers"); table = Table(csv_path); enrich(leads, table)
    rules = rules_path or best_rules()
    progress(f"judging with {os.path.basename(rules)}")
    verdicts = Critic().judge_all(leads, table, rules)
    by_id = {l["id"]: l for l in leads}
    judged = [{**by_id[v["lead_id"]], "label": v["label"], "confidence": v["confidence"], "reason": v["reason"]} for v in verdicts]
    survivors = [j for j in judged if j["label"] == "ok"]
    killed = [j for j in judged if j["label"] != "ok"]
    progress(f"done in {time.time()-t0:.0f}s: {len(survivors)} survive, {len(killed)} killed")
    return {"dataset": dataset, "summary": summary, "rules": rules, "leads": judged,
            "survivors": survivors, "killed": killed, "seconds": round(time.time() - t0)}


if __name__ == "__main__":
    out = run_pipeline(sys.argv[1], rules_path=sys.argv[2] if len(sys.argv) > 2 else None)
    os.makedirs("results", exist_ok=True)
    path = f"results/product_{out['dataset']}.json"; json.dump(out, open(path, "w"), indent=1)
    print(f"\n== {out['dataset']}: {len(out['survivors'])} survivors of {len(out['leads'])} (rules {os.path.basename(out['rules'])}) ==")
    for s in out["survivors"][:5]: print(f"  OK   {s['claim'][:90]}")
    for k in out["killed"][:5]: print(f"  {k['label']:13} {k['claim'][:70]} | {k['reason'][:60]}")
    print(f"-> {path}")
