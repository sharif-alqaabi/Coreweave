"""Build a labeled lead set for ANY OSDR study in one command (needs model credits, ~4 min):

    python3 scripts/make_golden.py OSD-99

Downloads the DGE table via the catalog, summarizes, generates 60 leads, enriches, jury-labels,
and writes data/golden/<study>.json ready for:  python3 loop.py --holdout --compare --holdout-file data/golden/<study>.json
"""
import csv, json, os, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sh(*cmd):
    print("$", " ".join(cmd)); subprocess.run(cmd, check=True)


def main(study):
    row = next(r for r in csv.DictReader(open("data/osdr_catalog.csv")) if r["osd_id"] == study)
    csv_path = f"data/raw/{study}_differential_expression.csv"
    if not os.path.exists(csv_path):
        print("downloading", row["dge_url"]); urllib.request.urlretrieve(row["dge_url"], csv_path)
    sh("python3", "helix/summarize.py", csv_path)
    sh("python3", "scripts/generate_leads.py", f"data/summaries/{study}.md", f"ledger/leads_{study}.json")
    from helix.critic_payload import Tables, enrich
    leads = json.load(open(f"ledger/leads_{study}.json"))
    for l in leads:
        l["id"] = f"{study}_{l['id']}"; l["dataset"] = study
    enrich(leads, Tables([csv_path]))
    json.dump(leads, open(f"ledger/leads_{study}_enriched.json", "w"), indent=1)
    sh("python3", "scripts/jury_labels.py", f"ledger/leads_{study}_enriched.json", f"data/golden/labels_{study}.jsonl")
    labels = {json.loads(x)["lead_id"]: json.loads(x) for x in open(f"data/golden/labels_{study}.jsonl")}
    for l in leads:
        l["label"] = labels[l["id"]]["label"]; l["label_note"] = labels[l["id"]].get("note", "")
    out = f"data/golden/{study}.json"; json.dump(leads, open(out, "w"), indent=1)
    print(f"\\n{len(leads)} labeled leads -> {out}\\nLive:  python3 loop.py --holdout --compare --holdout-file {out}")


if __name__ == "__main__":
    main(sys.argv[1])
