"""Build the research knowledge graph.

    python -m helix.graph.build                    # everything: corpus (cached), entities, TypeSafe edges, LLM explanations
    python -m helix.graph.build --max 40           # first 40 findings, for a quick look
    python -m helix.graph.build --no-numeric --no-explain

Writes results/graph.json: nodes (finding, passage, paper, dataset, gene, go, tissue) and edges (judged + structural).
Thresholds that decide which judged edges are kept live in ACCEPT below; every judged edge keeps its probabilities.
"""
import json, os, sys, time
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
from helix.graph import corpus as C, entities as E, edges as X, explain as EX
from helix.graph.entities import catalog_tissue
from helix import replicate as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT, ".env"))
OUT = os.path.join(ROOT, "results/graph.json")

ACCEPT = {                                    # code policy over Jev's answers, after relabel()
    "finding-passage": lambda e: e["relation"] in ("supports", "consistent", "contradicts", "background") and e["confidence"] >= 0.4,
    "finding-finding": lambda e: e["relation"] != "unrelated" and e["confidence"] >= 0.4,
    "finding-dataset": lambda e: e["relation"] in ("replicated", "contradicted", "not_replicated", "underpowered"),
}


def relabel(e, f_by):
    """Single-condition Nouls gate the Choice: 'supports' needs P(supports), 'contradicts' needs P(contradicts).
    A Choice with no admissible option becomes the weaker label. Same-dataset 'replicates' is a rediscovery, not a replication."""
    if e["type"] == "finding-passage":
        if e["relation"] == "supports":
            e["relation"] = "supports" if e["p_supports"] >= 0.5 else "consistent"
        elif e["relation"] == "contradicts" and e["p_contradicts"] < 0.5:
            e["relation"] = "background" if e["probabilities"].get("background", 0) >= 0.2 else "mentions_only"
    elif e["type"] == "finding-finding" and e["relation"] == "replicates":
        a, b = f_by[e["src"]], f_by[e["dst"]]
        if a["dataset"] == b["dataset"]:
            e["relation"] = "rediscovers" if "paper_claim" in (a["kind"], b["kind"]) else "restates"
    return e


def assemble(findings, passages, edges, papers, studies):
    p_by = {p["id"]: p for p in passages}; f_by = {f["id"]: f for f in findings}
    kept = [e for e in (relabel(e, f_by) for e in edges) if ACCEPT[e["type"]](e)]
    for k, e in enumerate(kept):
        e["id"] = f"e{k}"
    nodes, ids = [], set()

    def add(nid, ntype, label, **attrs):
        if nid not in ids:
            ids.add(nid); nodes.append({"id": nid, "type": ntype, "label": label, **attrs})
    for f in findings:
        add(f["id"], "finding", f["claim"][:90], kind=f["kind"], status=f["status"], dataset=f["dataset"], shape=f["shape"], claim=f["claim"],
            genes=f["genes"], go=f["go"], why_not_known=f["why_not_known"], next_step=f["next_step"], reason=f["reason"],
            numbers={g: {x: v[x] for x in ("log2fc", "padj", "higher_group", "carriers") if x in v} for g, v in f["table_facts"].items() if isinstance(v, dict) and "log2fc" in v})
    struct = []
    used_passages = {e["dst"] for e in kept if e["type"] == "finding-passage"}
    for pid in used_passages:
        p = p_by[pid]
        add(pid, "passage", p["text"][:80], text=p["text"], section=p["section"], source=p["source"], pmid=p["pmid"], osd_ids=p["osd_ids"], genes=p["genes"])
        if p["pmid"]:
            pp = papers.get(p["pmid"], {})
            add("pmid" + p["pmid"], "paper", pp.get("title", "")[:90], title=pp.get("title", ""), journal=pp.get("journal", ""), year=pp.get("year", ""),
                doi=pp.get("doi", ""), pmid=p["pmid"], osd_ids=pp.get("osd_ids", []))
            struct.append({"type": "passage-paper", "relation": "in", "src": pid, "dst": "pmid" + p["pmid"]})
            for o in pp.get("osd_ids", []):
                struct.append({"type": "paper-dataset", "relation": "about", "src": "pmid" + p["pmid"], "dst": o})
        for g in p["genes"]:
            struct.append({"type": "passage-gene", "relation": "mentions", "src": pid, "dst": "gene:" + g})
    datasets = {f["dataset"] for f in findings} | {e["dst"] for e in kept if e["type"] == "finding-dataset"} \
               | {o for n in nodes if n["type"] in ("passage", "paper") for o in n.get("osd_ids", [])}
    for d in sorted(datasets):
        row = R.study(d) or {}; st = studies.get(d, {})
        tis, fac = catalog_tissue(d)
        add(d, "dataset", f"{d} {row.get('material', '')[:30]}", organism=row.get("organism", ""), material=row.get("material", ""),
            factors=row.get("factors", ""), assay=row.get("assay", ""), title=st.get("title") or row.get("title", ""), tissues=tis, conditions=fac)
        for t in tis:
            add("tissue:" + t, "tissue", t); struct.append({"type": "dataset-tissue", "relation": "tissue", "src": d, "dst": "tissue:" + t})
    genes = {g.upper() for f in findings for g in f["genes"]} | {g for n in nodes if n["type"] == "passage" for g in n["genes"]}
    vocab = E.gene_vocab()
    for g in sorted(genes):
        add("gene:" + g, "gene", vocab.get(g, g))
    go_names = X._go_names()
    for f in findings:
        struct.append({"type": "finding-dataset", "relation": "from", "src": f["id"], "dst": f["dataset"]})
        for g in f["genes"]:
            struct.append({"type": "finding-gene", "relation": "mentions", "src": f["id"], "dst": "gene:" + g.upper()})
        for go in f["go"]:
            add(go, "go", go_names.get(go, go)); struct.append({"type": "finding-go", "relation": "mentions", "src": f["id"], "dst": go})
    for k, e in enumerate(struct):
        e["id"] = f"s{k}"
    return nodes, kept + struct, len(edges) - len(kept)


def main(argv):
    max_f = int(argv[argv.index("--max") + 1]) if "--max" in argv else None
    t0 = time.time()
    studies, papers, passages = C.build(fulltext=True, progress=lambda s: None) if not os.path.exists(os.path.join(C.DIR, "passages.jsonl")) \
        else (json.load(open(os.path.join(C.DIR, "studies.json"))), json.load(open(os.path.join(C.DIR, "papers.json"))), C.load_passages())
    print(f"corpus: {len(studies)} studies, {len(papers)} papers, {len(passages)} passages")
    from typesafe_sdk import TypeSafeClient
    with TypeSafeClient(timeout=120) as client:
        E.tag_passages(passages, client=client)
        findings = E.findings()[:max_f]
        print(f"{len(findings)} findings")
        edges = X.build_edges(findings, passages, client, numeric="--no-numeric" not in argv)
    nodes, all_edges, dropped = assemble(findings, passages, edges, papers, studies)
    if "--no-explain" not in argv:
        EX.explain_edges(all_edges, findings, passages)
    stats = {"nodes": Counter(n["type"] for n in nodes), "edges": Counter(f"{e['type']}:{e['relation']}" for e in all_edges),
             "judged_dropped": dropped, "seconds": round(time.time() - t0)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"built": time.strftime("%Y-%m-%d %H:%M"), "stats": stats, "nodes": nodes, "edges": all_edges}, open(OUT, "w"))
    print(json.dumps(stats, indent=1)); print("->", OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
