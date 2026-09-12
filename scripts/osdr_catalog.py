"""Catalog NASA OSDR studies that ship a processed differential-expression CSV.

Usage:  python3 scripts/osdr_catalog.py            # writes data/osdr_catalog.csv
        python3 scripts/osdr_catalog.py --rescore  # re-rank without re-fetching
No third-party deps: stdlib only, so it runs before `uv sync`.
"""
import csv, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

OSDR = "https://osdr.nasa.gov"
BATCH = 20          # study ids per files-API request
WORKERS = 4         # parallel requests


def get_json(url, timeout=180):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def search_studies():
    """Every GeneLab (cgene) study: id -> metadata dict from the search API."""
    d = get_json(f"{OSDR}/osdr/data/search?term=&type=cgene&size=2000&from=0")
    out = {}
    for hit in d["hits"]["hits"]:
        s = hit["_source"]
        sid = s["Study Identifier"]           # e.g. "OSD-104"
        out[sid] = {
            "osd_id": sid,
            "title": s.get("Study Title", ""),
            "organism": " | ".join(re.split(r"\s{2,}", s.get("organism", "").strip())),
            "project_type": s.get("Project Type", ""),
            "material": " | ".join(re.split(r"\s{2,}", s.get("Material Type", "").strip())),
            "factors": s.get("Study Factor Name", ""),
            "assay": s.get("Study Assay Technology Type", ""),
        }
    return out


def dge_files(ids):
    """For a batch of numeric ids, return {osd_id: [download_url, ...]} for DGE csvs."""
    d = get_json(f"{OSDR}/osdr/data/osd/files/{','.join(ids)}?all_files=true")
    found = {}
    for sid, study in d.get("studies", {}).items():
        urls = [OSDR + f["remote_url"] for f in study["study_files"]
                if "differential_expression" in f["file_name"].lower()
                and f["file_name"].endswith(".csv")]
        if urls:
            found[sid] = urls
    return found


def probe_header(url):
    """Read the first ~64KB of a DGE csv and describe its design from the header."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-65535"})
    with urllib.request.urlopen(req, timeout=120) as r:
        header = r.read().decode("utf-8", "replace").split("\n", 1)[0]
    cols = next(csv.reader([header]))
    groups = [re.match(r"Group\.Mean_\((.*)\)$", c).group(1)
              for c in cols if c.startswith("Group.Mean_(")]
    contrasts = sum(c.startswith("Log2fc_(") for c in cols)
    first_stat = next((i for i, c in enumerate(cols) if c.startswith("Log2fc_(")), len(cols))
    annot = {"ENSEMBL", "SYMBOL", "GENENAME", "REFSEQ", "ENTREZID", "STRING_id", "GOSLIM_IDS", ""}
    n_samples = sum(c not in annot for c in cols[:first_stat])
    return {"n_samples": n_samples, "n_groups": len(groups),
            "n_contrasts": contrasts // 2,        # each pair appears as AvB and BvA
            "groups": " | ".join(groups)}


def score(row):
    """Higher = better source for a first golden set. Simple, explainable rules."""
    s = 0
    s += 2 * ("Spaceflight" in row["project_type"])
    s += 3 * (row["n_groups"] == 2)              # one clean contrast
    s += 1 * (row["n_samples"] >= 10)            # >=5 per group if 2 groups
    s -= 1 * (row["n_contrasts"] > 6)            # factorial designs are confusing
    return s


def rescore(path="data/osdr_catalog.csv"):
    """Re-rank an existing catalog after editing score(); no network calls."""
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for k in ("n_samples", "n_groups", "n_contrasts"):
            r[k] = int(r[k])
        r["score"] = score(r)
    rows.sort(key=lambda r: (-r["score"], int(r["osd_id"].split("-")[1])))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"rescored {len(rows)} rows -> {path}", file=sys.stderr)


def main(out_path="data/osdr_catalog.csv"):
    if out_path == "--rescore":
        return rescore()
    studies = search_studies()
    print(f"{len(studies)} cgene studies from search API", file=sys.stderr)
    nums = sorted(int(s.split("-")[1]) for s in studies if re.fullmatch(r"OSD-\d+", s))
    batches = [[str(n) for n in nums[i:i + BATCH]] for i in range(0, len(nums), BATCH)]
    with ThreadPoolExecutor(WORKERS) as pool:
        with_dge = {}
        for found in pool.map(dge_files, batches):
            with_dge.update(found)
    print(f"{len(with_dge)} studies have a differential_expression csv", file=sys.stderr)

    def build(sid):
        url = sorted(with_dge[sid])[0]             # prefer the non-rRNArm variant
        row = dict(studies.get(sid, {"osd_id": sid}), dge_url=url)
        try:
            row.update(probe_header(url))
        except Exception as e:                     # header probe is best-effort
            row.update(n_samples=-1, n_groups=-1, n_contrasts=-1, groups=f"ERR {e}")
        row["score"] = score(row)
        return row

    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(build, sorted(with_dge)))
    rows.sort(key=lambda r: (-r["score"], int(r["osd_id"].split("-")[1])))
    fields = ["score", "osd_id", "organism", "project_type", "material", "factors",
              "n_samples", "n_groups", "n_contrasts", "groups", "assay", "title", "dge_url"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
