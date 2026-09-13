"""Edges of the graph. Code proposes candidate pairs from shared entities; TypeSafe (Jev) judges each pair's relationship
and returns probabilities; code applies thresholds. Nothing here writes prose.

    finding -> passage : supports / contradicts / background / mentions_only / unrelated   (+ P(supports) as a Noul)
    finding <-> finding: replicates / contradicts / extends / same_entity_different_claim / unrelated (+ P(same mechanism))
    finding -> dataset : replicated / contradicted / not_replicated / ... from the numbers (helix.replicate, gated by comparability)

Requests batch several candidates over one finding's state (independent questions, answered in parallel by the model).
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from helix.graph.entities import catalog_tissue
from helix import replicate as R

MAX_PASSAGES = 30               # candidate passages judged per finding
MAX_PEERS = 20                  # candidate findings judged per finding
BATCH = 8                       # candidates per request
WORKERS = 12

PASSAGE_RELATION = {
    "supports": "The passage reports this result or one that directly entails it: the same gene(s) or pathway changing in the same "
                "direction under a comparable condition, or the same global pattern",
    "contradicts": "The passage reports the opposite direction, or explicitly no change, for the same gene(s) or pathway under a comparable condition",
    "background": "The passage explains what the gene, pathway or tissue does, or a mechanism that would account for the finding, "
                  "without testing the finding itself",
    "mentions_only": "The gene, pathway or tissue is named but the passage says nothing that bears on the finding",
    "unrelated": "The passage is about something else",
}
FINDING_RELATION = {
    "replicates": "Both findings report the same gene(s) or pathway changing in the same direction, in a comparable tissue and condition, from different data",
    "contradicts": "Both findings concern the same gene(s) or pathway in a comparable tissue and condition but report opposite directions",
    "extends": "Both findings concern the same gene(s), family or pathway with a consistent direction, but in a different tissue, condition or level "
               "of description (a single gene and the family it belongs to; one tissue and another)",
    "same_entity_different_claim": "They share a gene or pathway but make claims about different things (a data-quality note versus an expression change)",
    "unrelated": "They share nothing meaningful",
}


def _go_names():
    p = os.path.join(R.ROOT, "data/go_names.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def _finding_state(f, tissues, factors):
    return {"id": f["id"], "claim": f["claim"], "shape": f["shape"], "genes": f["genes"], "go_terms": f["go"], "dataset": f["dataset"],
            "tissue": tissues, "condition": factors, "why_not_known": f["why_not_known"],
            "numbers": {k: {x: v[x] for x in ("log2fc", "padj", "higher_group", "carriers") if x in v} for k, v in list(f["table_facts"].items())[:6]
                        if isinstance(v, dict)}}


# ---------------------------------------------------------------- candidates
POOL = 120                      # passages per finding that enter the relevance rerank
RELEVANCE_BATCH = 12
GENERIC = {"region", "process", "activity", "complex", "cellular", "regulation", "binding", "positive", "negative", "part", "cell",
           "protein", "organization", "involved", "response", "metabolic", "biological"}


def _go_stems(name):
    return [w[:6] for w in re.findall(r"[a-z]{5,}", name.lower()) if w not in GENERIC]


def passage_pool(f, passages, by_gene, by_text, go_names, f_tissue, f_factor, by_osd, by_tissue):
    """Broad pool: shared genes, GO-term stems, the finding's own study's papers, and same-tissue same-condition passages.
    Ranked by a code prior and capped at POOL; Jev's relevance rerank picks the ones worth a relation judgment."""
    cand = {}
    for g in {g.upper() for g in f["genes"]}:
        for i in by_gene.get(g, ()):
            cand[i] = cand.get(i, 0) + 3
    for go in f["go"]:
        stems = _go_stems(go_names.get(go, ""))
        if stems:
            for i in by_text(stems):
                cand[i] = cand.get(i, 0) + 2
    for i in by_osd.get(f["dataset"], ()):                          # the study's own paper: where 'supports' lives
        cand[i] = cand.get(i, 0) + 1.5
    for t in f_tissue:
        for i in by_tissue.get(t, ()):
            p = passages[i]
            if set(f_factor) & set(p["factors"]):
                cand[i] = cand.get(i, 0) + 0.5
    scored = []
    for i, prior in cand.items():
        p = passages[i]
        prior += 0.5 * (p["source"] == "abstract") + 0.3 * (p["section"].lower().startswith(("result", "discussion")))
        scored.append((prior, i))
    return [i for _, i in sorted(scored, reverse=True)[:POOL]]


def rerank(f, state, pool, passages, client, keep=MAX_PASSAGES):
    """Stage 1: one Noul per passage, batched, over the finding's state. Keeps the top `keep` by P(relevant)."""
    from typesafe_sdk import Noul
    rel = {}
    for b in range(0, len(pool), RELEVANCE_BATCH):
        batch = pool[b:b + RELEVANCE_BATCH]
        st = {"finding": state, "passages": [passages[i]["text"] for i in batch]}
        qs = {f"r{j}": Noul(instructions=f"Does `passages[{j}]` bear on `finding`: does it report, contradict, or explain the same gene(s), "
                                         f"pathway, or tissue-level process under a comparable condition? Not merely the same organism or mission.")
              for j in range(len(batch))}
        try:
            r = client.system_one(state=st, questions=qs)
        except Exception:
            continue
        for j, i in enumerate(batch):
            rel[i] = r.answers[f"r{j}"].noul
    ranked = sorted(rel, key=lambda i: -rel[i])
    return [i for i in ranked[:keep] if rel[i] >= 0.25], rel


def peer_candidates(f, findings, gene_index, go_index):
    """Other findings sharing a gene or GO term, different datasets first, capped."""
    cand = {}
    for g in f["genes"]:
        for j in gene_index.get(g.upper(), ()):
            cand[j] = cand.get(j, 0) + 1
    for go in f["go"]:
        for j in go_index.get(go, ()):
            cand[j] = cand.get(j, 0) + 1
    cand.pop(f["_i"], None)
    scored = sorted(((shared + 2 * (findings[j]["dataset"] != f["dataset"]) + (findings[j]["kind"] == "paper_claim"), j)
                     for j, shared in cand.items()), reverse=True)
    return [j for _, j in scored[:MAX_PEERS]]


# ---------------------------------------------------------------- judgments
def judge_passages(f, state, cands, passages, client):
    from typesafe_sdk import Choice, Noul
    out = []
    for b in range(0, len(cands), BATCH):
        batch = cands[b:b + BATCH]
        st = {"finding": state, "passages": [{"id": passages[i]["id"], "section": passages[i]["section"], "text": passages[i]["text"],
                                               "from_same_study": f["dataset"] in passages[i]["osd_ids"]} for i in batch]}
        qs = {}
        for j in range(len(batch)):
            qs[f"p{j}_supports"] = Noul(instructions=f"Does `passages[{j}].text` state or establish `finding.claim`: the same gene(s) or pathway, "
                                                     f"the same direction of change, under a comparable condition and tissue? Naming the gene is not enough.")
            qs[f"p{j}_contradicts"] = Noul(instructions=f"Does `passages[{j}].text` report the OPPOSITE direction of change, or explicitly no change, "
                                                        f"for the same gene(s) or pathway as `finding.claim` under a comparable condition and tissue? "
                                                        f"Listing the gene, or discussing a different tissue or condition, is not a contradiction.")
            qs[f"p{j}_relation"] = Choice(instructions=f"How does `passages[{j}].text` relate to `finding.claim`?", criteria=PASSAGE_RELATION)
        try:
            r = client.system_one(state=st, questions=qs)
        except Exception as e:
            continue
        for j, i in enumerate(batch):
            c = r.answers[f"p{j}_relation"]
            out.append({"type": "finding-passage", "src": f["id"], "dst": passages[i]["id"], "relation": c.choice,
                        "p_supports": round(r.answers[f"p{j}_supports"].noul, 3), "p_contradicts": round(r.answers[f"p{j}_contradicts"].noul, 3),
                        "confidence": round(c.confidence, 3),
                        "probabilities": {k: round(v, 3) for k, v in c.probabilities.items()}})
    return out


def judge_peers(f, state, cands, findings, states, client):
    from typesafe_sdk import Choice, Noul
    out = []
    for b in range(0, len(cands), BATCH):
        batch = cands[b:b + BATCH]
        st = {"finding": state, "others": [states[j] for j in batch]}
        qs = {}
        for j in range(len(batch)):
            qs[f"o{j}_relation"] = Choice(instructions=f"How does `others[{j}]` relate to `finding`? Compare genes or pathway, direction "
                                                       f"(`numbers`), tissue and condition.", criteria=FINDING_RELATION)
            qs[f"o{j}_mechanism"] = Noul(instructions=f"Do `finding` and `others[{j}]` plausibly reflect the same underlying biological "
                                                      f"mechanism (for example the same proliferation shutdown, the same stress response)?")
        try:
            r = client.system_one(state=st, questions=qs)
        except Exception as e:
            continue
        for j, k in enumerate(batch):
            c = r.answers[f"o{j}_relation"]
            out.append({"type": "finding-finding", "src": f["id"], "dst": findings[k]["id"], "relation": c.choice,
                        "p_mechanism": round(r.answers[f"o{j}_mechanism"].noul, 3), "confidence": round(c.confidence, 3),
                        "probabilities": {k2: round(v, 3) for k2, v in c.probabilities.items()}})
    return out


def numeric_edges(f, own_row, tables, comparability, client):
    """finding -> dataset edges from the numbers, via helix.replicate (Tier 2 with the Tier 1 comparability gate)."""
    if not f["genes"] and not f["go"]:
        return []
    lead = {**f, "rows": f["genes"] + f["go"]}
    looked = [(oid, R.study(oid), R.numeric_facts(lead, t), comparability.get(oid, 0)) for oid, t in tables.items() if oid != f["dataset"]]
    looked = [(oid, m, fx, lvl) for oid, m, fx, lvl in looked if fx and not all(isinstance(x, dict) and "error" in x for x in fx.values())]
    if not looked:
        return []
    try:
        vs = R.replication_verdicts(lead, own_row, looked, client)
    except Exception:
        return []
    return [{"type": "finding-dataset", "src": f["id"], "dst": v["osd_id"], "relation": v["verdict"], "jev_verdict": v["jev_verdict"],
             "comparable": v["comparable"], "agreement": v["agreement"], "p_replicated": v["p_replicated"],
             "p_contradicted": v["p_contradicted"], "confidence": v["confidence"],
             "numbers": {g: {x: fx[x] for x in ("log2fc", "padj", "higher_group", "carriers") if x in fx} for g, fx in v["facts"].items() if isinstance(fx, dict) and "log2fc" in fx}}
            for v in vs]
