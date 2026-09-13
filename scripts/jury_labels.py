"""Golden labels from a jury of models with an expert rubric (not the critic's rules).

    python3 scripts/jury_labels.py ledger/leads_enriched.json data/golden/labels.jsonl

Annotator A and B label every lead independently. Agreement -> label. Disagreement ->
adjudicator picks; the note records both views. Models differ from the critic (WANDB_MODEL).
Disclose this to judges: "two-model jury + adjudicator, expert rubric, critic is a different model."
"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from helix.critic_payload import Table, enrich, OPTIONS
from helix import llm

load_dotenv(".env")
JURY = {"A": os.getenv("JURY_A", "deepseek-ai/DeepSeek-V3.1"),
        "B": os.getenv("JURY_B", "openai/gpt-oss-120b"),
        "adjudicator": os.getenv("JURY_C", "moonshotai/Kimi-K2.6")}

RUBRIC = f"""You are a senior muscle physiologist and RNA-seq statistician labeling research leads
from a mouse spaceflight study (soleus muscle, 6 flight vs 6 ground). Label ONE lead with exactly
one option from {OPTIONS}. Use these definitions strictly, in this priority order:

1. contradicted: table_facts disagree with the claim (wrong direction, padj > 0.05, gene absent).
2. confound: the signal comes from a MINORITY of samples (carriers strictly below half of the
   higher group, e.g. 2/6) or the claim depends on flagged samples. 4/6 or 5/6 is NOT a confound.
3. underpowered: mean count in the higher group < 20, or padj in (0.01, 0.05) with carriers <= 3.
4. untestable: the "lead" is a restated statistic with no biological or methodological claim
   ("gene X is reliably detected", "median |log2fc| is 0.36"), or next_step is vague/absent.
5. already_known: the claim is textbook for this system. In a hindlimb-unloading / spaceflight
   muscle atrophy model, enrichment of sarcomere, myofibril, Z disc, I band, contractile fiber and
   muscle-development terms is expected and published; so is downregulation of structural muscle
   genes. Label already_known unless the lead names a specific NEW angle (a subset, a direction
   split, a mechanism not in the literature).
6. no_mechanism: numbers hold but the gene is unannotated / predicted (Gm prefix) and no mechanism
   is offered.
7. ok: none of the above; the claim is supported, non-obvious, and has a concrete next step.
   Global patterns with a real claim (e.g. "more genes down than up" with a stated interpretation)
   can be ok. A data-quality lead that identifies a real problem (flagged samples driving top hits)
   is ok.

Reply with JSON only: {{"label": <option>, "note": "<one sentence with the deciding number/reason>"}}"""


def ask(model, lead):
    body = {k: lead[k] for k in ("claim", "shape", "why_not_known", "next_step", "table_facts")}
    text = llm.chat(RUBRIC, json.dumps(body), model=model, max_tokens=600) or ""
    try:
        s, e = text.index("{"), text.rindex("}") + 1
        out = json.loads(text[s:e])
        return (out["label"] if out.get("label") in OPTIONS else "invalid"), out.get("note", "")
    except Exception:
        return "invalid", text[:100]


def main(leads_path, out_path):
    leads = json.load(open(leads_path))
    agree = 0
    with open(out_path, "w") as f:
        for lead in leads:
            a, na = ask(JURY["A"], lead); b, nb = ask(JURY["B"], lead)
            if a == b and a != "invalid":
                label, note, how = a, na, "agree"; agree += 1
            else:
                votes = json.dumps({"A": {"label": a, "note": na}, "B": {"label": b, "note": nb}})
                c, nc = ask(JURY["adjudicator"], {**lead, "why_not_known": lead["why_not_known"] + f"\n[Two annotators disagreed: {votes}. Decide.]"})
                label, note, how = (c if c != "invalid" else (a if a != "invalid" else b)), f"A={a}; B={b}; adjudicated: {nc}", "adjudicated"
            f.write(json.dumps({"lead_id": lead["id"], "label": label, "note": note, "how": how,
                                "jury": {"A": a, "B": b}}) + "\n")
            print(f"{lead['id']} {label:15} [{how:11}] {note[:70]}")
    print(f"\nagreement: {agree}/{len(leads)}  ->  {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
