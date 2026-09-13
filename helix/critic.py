"""The critic: one label per lead, from the payload and the current rules.

    critic = Critic(model="claude-sonnet-5")          # or Critic(dry_run=True)
    verdicts = critic.judge_all(leads, table, rules_path)

Each verdict: {"lead_id", "label", "confidence", "reason", "rules_version"}.
Dry-run mode applies three crude numeric rules so the pipeline can be tested without a key.
"""
import json, os, re
from helix.critic_payload import build_payload, OPTIONS
from helix import llm

SYSTEM = ("You are a strict scientific critic. Read the lead, the true table facts, and the rules. "
          "Choose exactly one option. Reply with JSON only: "
          '{"label": <option>, "confidence": <0-1>, "reason": "<one sentence citing a number or rule>"}')


def _dry_label(payload):
    facts = payload["input"]["table_facts"]
    for g, f in facts.items():
        if "error" in f:
            return "contradicted", 0.9, f"{g} not in table"
        if "padj" in f:
            if f["padj"] > 0.05:
                return "contradicted", 0.85, f"{g} padj={f['padj']:.2g} > 0.05"
            n, d = map(int, f["carriers"].split("/"))
            if n * 2 < d:
                return "confound", 0.8, f"{g} carriers {f['carriers']}"
    if not payload["input"]["next_step"].strip():
        return "untestable", 0.7, "no next_step"
    return "ok", 0.6, "no rule fired"


try:
    import weave
    traced = weave.op()
except Exception:                                   # weave missing: plain functions
    def traced(fn): return fn


class Critic:
    def __init__(self, model=None, dry_run=False):
        self.model = model or os.getenv("CRITIC_MODEL")        # None -> provider default (helix/llm.py)
        self.dry_run = dry_run

    @traced
    def judge(self, payload):
        if self.dry_run:
            label, conf, reason = _dry_label(payload)
        else:
            text = llm.chat(SYSTEM, json.dumps(payload), model=self.model, max_tokens=400)
            out = {}
            for m in re.finditer(r"\{.*?\}", text, re.S):          # first parseable JSON object wins
                try:
                    out = json.loads(m.group()); break
                except json.JSONDecodeError:
                    continue
            if not out:                                             # truncated / malformed: salvage the label
                lab = re.search(r'"label"\s*:\s*"(\w+)"', text)
                out = {"label": lab.group(1) if lab else "ok", "confidence": 0.0, "reason": "unparseable critic output"}
            label, conf, reason = out.get("label", "ok"), float(out.get("confidence", 0.5)), out.get("reason", "")
        if label not in OPTIONS:
            label, conf, reason = "ok", 0.0, f"invalid label from critic: {label}"
        return {"label": label, "confidence": conf, "reason": reason}

    def judge_all(self, leads, table, rules_path, workers=8):
        """Judge every lead; calls are independent so they run in parallel (order preserved)."""
        from concurrent.futures import ThreadPoolExecutor
        rules_dir, fname = os.path.split(rules_path)
        version = int(re.search(r"v(\d+)", fname).group(1))
        payloads = [build_payload(lead, table, rules_dir=rules_dir, rules_file=fname) for lead in leads]
        with ThreadPoolExecutor(workers if not self.dry_run else 1) as pool:
            verdicts = list(pool.map(self.judge, payloads))
        return [{"lead_id": lead["id"], "rules_version": version, **v} for lead, v in zip(leads, verdicts)]
