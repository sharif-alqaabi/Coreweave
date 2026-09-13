"""Split labeled leads into train (the loop sees these) and holdout (opened once, at the end).

    python3 scripts/split_golden.py ledger/leads_enriched.json data/golden/labels.jsonl

Writes data/golden/train.json and data/golden/holdout.json, each holding leads with
their human label attached. Stratified by (dataset, shape) so both halves have the same mix.
"""
import json, random, sys
from collections import defaultdict
from pathlib import Path

def main(leads_path, labels_path, out_dir="data/golden", seed=0):
    leads = json.load(open(leads_path))
    labels = {json.loads(l)["lead_id"]: json.loads(l) for l in open(labels_path) if l.strip()}
    missing = [l["id"] for l in leads if l["id"] not in labels]
    if missing:
        sys.exit(f"{len(missing)} leads have no human label yet: {missing[:5]}...")
    by_shape = defaultdict(list)
    for l in leads:
        l["label"] = labels[l["id"]]["label"]
        l["label_note"] = labels[l["id"]].get("note", "")
        by_shape[(l.get("dataset", "?"), l.get("shape", "?"))].append(l)   # stratify by dataset AND shape
    rng, train, holdout = random.Random(seed), [], []
    for shape, group in sorted(by_shape.items()):
        rng.shuffle(group)
        half = len(group) // 2
        train += group[:half]; holdout += group[half:]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json.dump(train, open(f"{out_dir}/train.json", "w"), indent=1)
    json.dump(holdout, open(f"{out_dir}/holdout.json", "w"), indent=1)
    print(f"train={len(train)} holdout={len(holdout)}  (do not open holdout until the end)")

if __name__ == "__main__":
    main(*sys.argv[1:])
