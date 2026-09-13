"""The prose layer: a regular LLM writes one sentence per accepted edge and quotes the passage span that carries it.
Runs only on edges TypeSafe has already accepted, so it is cheap; skipped cleanly when no LLM key is configured.

    explain_edges(edges, findings, passages)   -> adds edge["explanation"], edge["quote"]
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from helix import llm

BATCH = 8
SYSTEM = ("You annotate edges of a research knowledge graph. For each edge you get a finding, a related text (a passage from a paper, "
          "or another finding), and the relationship a scoring model assigned. Write ONE sentence (max 35 words) that explains why the "
          "relationship holds, naming the gene/pathway and direction and citing a number when one is present. For passage edges also "
          "copy a `quote`: an exact, verbatim substring of the passage (max 25 words) that carries the relationship; for finding edges "
          "leave quote empty. Never invent numbers. Reply with JSON only: a list of {\"i\": <index>, \"explanation\": ..., \"quote\": ...}.")


def available():
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("WANDB_API_KEY") or os.getenv("OPENAI_API_KEY"))


def _item(i, e, f_by, p_by):
    f = f_by[e["src"]]
    item = {"i": i, "relation": e["relation"], "finding": {"claim": f["claim"], "dataset": f["dataset"],
            "numbers": {k: {x: v[x] for x in ("log2fc", "padj", "higher_group") if x in v} for k, v in list(f["table_facts"].items())[:4] if isinstance(v, dict)}}}
    if e["type"] == "finding-passage":
        p = p_by[e["dst"]]; item["passage"] = {"section": p["section"], "text": p["text"]}
    else:
        o = f_by[e["dst"]]; item["other_finding"] = {"claim": o["claim"], "dataset": o["dataset"]}
    return item


def explain_edges(edges, findings, passages, progress=print, workers=6):
    if not available():
        progress("no LLM key (ANTHROPIC_API_KEY / WANDB_API_KEY / OPENAI_API_KEY): explanations skipped")
        return edges
    f_by = {f["id"]: f for f in findings}; p_by = {p["id"]: p for p in passages}
    todo = [e for e in edges if e["type"] in ("finding-passage", "finding-finding") and "explanation" not in e]
    batches = [todo[b:b + BATCH] for b in range(0, len(todo), BATCH)]

    def one(batch):
        items = [_item(i, e, f_by, p_by) for i, e in enumerate(batch)]
        try:
            text = llm.chat(SYSTEM, json.dumps(items), max_tokens=1800)
            m = re.search(r"\[.*\]", text, re.S)
            for r in json.loads(m.group()) if m else []:
                e = batch[int(r["i"])]
                e["explanation"] = str(r.get("explanation", ""))[:300]
                q = str(r.get("quote", "")).strip()
                if e["type"] == "finding-passage" and q and q not in p_by[e["dst"]]["text"]:
                    q = ""                                            # the quote must be verbatim, or it is not a quote
                e["quote"] = q
        except Exception as ex:
            for e in batch:
                e.setdefault("explanation", ""); e.setdefault("explain_error", f"{type(ex).__name__}"[:40])
        return len(batch)
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for n in ex.map(one, batches):
            done += n
            if done % 200 < BATCH:
                progress(f"  explained {done}/{len(todo)} edges")
    progress(f"explained {sum(1 for e in todo if e.get('explanation'))}/{len(todo)} edges")
    return edges
