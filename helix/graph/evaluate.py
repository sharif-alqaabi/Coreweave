"""Score TypeSafe's finding-passage judgments against human labels, and export edges for labelling.

    python -m helix.graph.evaluate                       # precision / recall / F1 per relation on data/golden/graph_pairs.jsonl
    python -m helix.graph.evaluate --export 60           # results/graph_pairs_to_label.csv: a stratified sample to label

Labels file: one JSON object per line: {finding_id, passage_id, relation, labeller, note}. Relations: supports (states the
result), consistent (entails it at the pathway level), contradicts, background, mentions_only, unrelated. A pair the graph
dropped counts as 'unrelated' (the build kept only supports/consistent/contradicts/background). The seed labels are the
developer's spot checks during the build and are marked as such; replace them with a scientist's before quoting a number.
"""
from __future__ import annotations
import argparse, csv, json, os, random, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from helix.settings import ROOT

LABELS = os.path.join(ROOT, "data/golden/graph_pairs.jsonl")
GRAPH = os.path.join(ROOT, "results/graph.json")
RELATIONS = ["supports", "consistent", "contradicts", "background", "mentions_only", "unrelated"]


def load_labels(path=LABELS):
    return [json.loads(l) for l in open(path) if l.strip()]


def predictions(graph, pairs):
    edges = {(e["src"], e["dst"]): e for e in graph["edges"] if e["type"] == "finding-passage"}
    rows = []
    for p in pairs:
        e = edges.get((p["finding_id"], p["passage_id"]))
        rows.append({**p, "predicted": e["relation"] if e else "unrelated",
                     "p_supports": e.get("p_supports") if e else None, "p_contradicts": e.get("p_contradicts") if e else None})
    return rows


def report(rows):
    from sklearn.metrics import classification_report, confusion_matrix
    y, yhat = [r["relation"] for r in rows], [r["predicted"] for r in rows]
    labels = [l for l in RELATIONS if l in set(y) | set(yhat)]
    print(f"{len(rows)} labelled pairs from {Counter(r['labeller'] for r in rows)}")
    print(classification_report(y, yhat, labels=labels, zero_division=0))
    print("confusion (rows = human, columns = TypeSafe):", labels)
    for lab, row in zip(labels, confusion_matrix(y, yhat, labels=labels)):
        print(f"  {lab:14}", " ".join(f"{v:3d}" for v in row))
    wrong = [r for r in rows if r["relation"] != r["predicted"]]
    for r in wrong:
        print(f"  miss: {r['finding_id']} <- {r['passage_id']}: human {r['relation']}, TypeSafe {r['predicted']} (P(sup) {r['p_supports']}, P(con) {r['p_contradicts']})")
    return {"n": len(rows), "accuracy": round(sum(r["relation"] == r["predicted"] for r in rows) / len(rows), 3)}


def export(graph, n, out):
    """A stratified sample of kept edges, with the text, for a person to label in a spreadsheet."""
    N = {x["id"]: x for x in graph["nodes"]}
    by_rel = {}
    for e in graph["edges"]:
        if e["type"] == "finding-passage":
            by_rel.setdefault(e["relation"], []).append(e)
    random.seed(0); sample = []
    per = max(1, n // max(1, len(by_rel)))
    for rel, es in by_rel.items():
        sample += random.sample(es, min(per, len(es)))
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["finding_id", "passage_id", "typesafe_relation", "p_supports", "p_contradicts", "claim", "passage", "your_label", "note"])
        for e in sample:
            w.writerow([e["src"], e["dst"], e["relation"], e["p_supports"], e.get("p_contradicts"), N[e["src"]]["claim"], N[e["dst"]]["text"], "", ""])
    print(f"{len(sample)} edges -> {out}; fill your_label with one of {RELATIONS} and convert to graph_pairs.jsonl")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=LABELS); ap.add_argument("--graph", default=GRAPH)
    ap.add_argument("--export", type=int, metavar="N")
    a = ap.parse_args(argv)
    graph = json.load(open(a.graph))
    if a.export:
        export(graph, a.export, os.path.join(ROOT, "results/graph_pairs_to_label.csv")); return
    report(predictions(graph, load_labels(a.labels)))


if __name__ == "__main__":
    main()
