"""The critic: one label per lead, from the payload and the current rules.

    critic = Critic(model="claude-sonnet-5")          # or Critic(dry_run=True)
    verdicts = critic.judge_all(leads, table, rules_path)

Each verdict: {"lead_id", "label", "confidence", "reason", "rules_version"}.
Dry-run mode applies three crude numeric rules so the pipeline can be tested without a key.
"""
import json, os, re
from helix.critic_payload import build_payload, OPTIONS

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


class Critic:
    def __init__(self, model=None, dry_run=False):
        self.model = model or os.getenv("CRITIC_MODEL", "claude-sonnet-5")
        self.dry_run = dry_run
        self.client = None
        if not dry_run:
            import anthropic                                   # lazy: only needed for real runs
            self.client = anthropic.Anthropic()

    def judge(self, payload):
        if self.dry_run:
            label, conf, reason = _dry_label(payload)
        else:
            msg = self.client.messages.create(
                model=self.model, max_tokens=300, system=SYSTEM,
                messages=[{"role": "user", "content": json.dumps(payload)}])
            text = msg.content[0].text
            m = re.search(r"\{.*\}", text, re.S)
            out = json.loads(m.group()) if m else {}
            label, conf, reason = out.get("label", "ok"), float(out.get("confidence", 0.5)), out.get("reason", "")
        if label not in OPTIONS:
            label, conf, reason = "ok", 0.0, f"invalid label from critic: {label}"
        return {"label": label, "confidence": conf, "reason": reason}

    def judge_all(self, leads, table, rules_path):
        rules_dir, fname = os.path.split(rules_path)
        version = int(re.search(r"v(\d+)", fname).group(1))
        out = []
        for lead in leads:
            payload = build_payload(lead, table, rules_dir=rules_dir, rules_file=fname)
            v = self.judge(payload)
            out.append({"lead_id": lead["id"], "rules_version": version, **v})
        return out
