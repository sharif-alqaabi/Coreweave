"""LLM-proposed golden labels for human review. Humans edit the output; they do not start blank.

    python3 scripts/propose_labels.py ledger/leads_enriched.json data/golden/labels_proposed.jsonl

Judges each lead independently (same payload the critic sees, rules v0), so proposals are
consistent and cite numbers. Review, edit, save as data/golden/labels.jsonl.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from helix.critic_payload import Table, build_payload, OPTIONS
from helix import llm

load_dotenv(".env")
SYSTEM = ("You are helping two scientists build an answer key for a hypothesis critic. Label ONE lead "
          "with exactly one option. Trust table_facts over the claim. A 'lead' must be a testable claim "
          "about the biology or the data; a restatement of a statistic with no claim is untestable. "
          f"Options: {OPTIONS}. Reply with JSON only: "
          '{"label": <option>, "note": "<one sentence with the deciding number or reason>"}')


def main(leads_path, out_path, table_path="data/raw/OSD-104_rna_seq_differential_expression.csv"):
    leads = json.load(open(leads_path))
    table = Table(table_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        for lead in leads:
            payload = build_payload(lead, table)
            text = llm.chat(SYSTEM, json.dumps(payload["input"]), max_tokens=200)
            try:
                s, e = text.index("{"), text.rindex("}") + 1
                out = json.loads(text[s:e])
                label = out.get("label") if out.get("label") in OPTIONS else "REVIEW"
                note = out.get("note", "")
            except Exception:
                label, note = "REVIEW", text[:120]
            f.write(json.dumps({"lead_id": lead["id"], "label": label, "note": note, "proposed_by": "llm"}) + "\n")
            print(f"{lead['id']} {label:18} {note[:80]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
