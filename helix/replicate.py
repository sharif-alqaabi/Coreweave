"""Novelty check: the survivors of a run against every other NASA OSDR dataset, judged by TypeSafe (Jev).

    from helix.replicate import check_novelty
    out = check_novelty("results/product_OSD-421.json")      # ~2 min for 38 survivors
    out["leads"][0]["verdict"], out["leads"][0]["where_to_look"], out["leads"][0]["numeric"]

The scout writes "not replicated in other spaceflight studies" into why_not_known; nobody checks. This does:

Tier 1, catalog (all 243 studies, no downloads): for every survivor and every same-organism study, Jev scores
    how well the study could replicate or refute the lead (Score) and whether it tests the same factor (Noul).
Tier 2, numeric (datasets on disk): pandas looks the lead's genes up in each other table; Jev judges what the
    two sets of numbers mean together (Choice: replicated / contradicted / not_detected / underpowered / inconclusive).
Numbers and thresholds stay in code; Jev only supplies the semantic judgment. Verdict per lead is a code rule.
"""
import csv, glob, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from helix.critic_payload import Table

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
CATALOG = os.path.join(ROOT, "data/osdr_catalog.csv")
CHUNK = 20                       # studies judged per request (one Score + one Noul each)
WORKERS = 8

COMPARABLE = ["Not comparable: different organism, no gene-expression assay, or unrelated experimental factor",
              "Weak context: same organism and factor but an unrelated tissue or cell type",
              "Related: same organism and factor, a tissue or cell type where the same biology plausibly applies",
              "Direct test: same organism, same factor, same or equivalent tissue"]

REPLICATION = {
    "replicated": "The other dataset shows the same genes changing in the same direction with padj below 0.05 "
                  "and most samples carrying the signal",
    "contradicted": "The other dataset shows the opposite direction with padj below 0.05 for the claimed genes, "
                    "in a tissue where the claim should hold",
    "not_replicated": "The other dataset measures the claimed genes in a comparable tissue and sees no significant change "
                      "(padj above 0.05); the lead is not confirmed there, which is weaker evidence than a contradiction",
    "not_detected": "The genes are absent from the other table or have near-zero counts, so it says nothing",
    "underpowered": "The other dataset points the same way but with padj above 0.05, few carriers, or low counts",
    "inconclusive": "The tissue or factor is too different for agreement or disagreement to mean anything",
}


def catalog():
    return list(csv.DictReader(open(CATALOG)))


def study(osd_id):
    return next((r for r in catalog() if r["osd_id"] == osd_id), None)


def _meta(row):
    return {k: row[k] for k in ("osd_id", "organism", "project_type", "material", "factors", "assay", "title", "n_samples")}


def _lead_state(lead, own):
    return {"claim": lead["claim"], "shape": lead["shape"], "genes": lead.get("rows", []),
            "dataset": lead["dataset"], "organism": own["organism"], "tissue": own["material"],
            "factor": own["factors"], "why_not_known": lead.get("why_not_known", "")}


def _client():
    from typesafe_sdk import TypeSafeClient
    return TypeSafeClient(timeout=120)


# ---------------------------------------------------------------- Tier 1: catalog
def catalog_scores(lead, own, studies, client):
    """One request per CHUNK studies: Score comparability + Noul same-factor for each, over the same lead state."""
    from typesafe_sdk import Score, Noul
    out = []
    for i in range(0, len(studies), CHUNK):
        chunk = studies[i:i + CHUNK]
        state = {"lead": _lead_state(lead, own), "studies": [_meta(r) for r in chunk]}
        qs = {}
        for j in range(len(chunk)):
            qs[f"s{j}_comparable"] = Score(
                instructions=f"How well could `studies[{j}]` replicate or refute `lead`? Judge organism, experimental "
                             f"factor (`lead.factor` vs `studies[{j}].factors`), assay, and whether `studies[{j}].material` "
                             f"is the same tissue as `lead.tissue` or one where the same biology applies.",
                criteria=COMPARABLE)
            qs[f"s{j}_same_factor"] = Noul(
                instructions=f"Does `studies[{j}]` test the same experimental factor as `lead.factor` "
                             f"(e.g. spaceflight vs ground control, or a ground analog of it like hindlimb unloading)?")
        r = client.system_one(state=state, questions=qs)
        for j, row in enumerate(chunk):
            sc = r.answers[f"s{j}_comparable"]
            out.append({"osd_id": row["osd_id"], "material": row["material"], "factors": row["factors"],
                        "assay": row["assay"][:40], "title": row["title"], "n_samples": row["n_samples"],
                        "comparable": round(sc.score, 2), "p_direct": round(sc.probabilities.get(3, 0.0), 2),
                        "confidence": round(sc.confidence, 2),
                        "same_factor": round(r.answers[f"s{j}_same_factor"].noul, 2), "on_disk": bool(local_csv(row["osd_id"]))})
    return sorted(out, key=lambda s: (-s["comparable"], -s["same_factor"]))


# ---------------------------------------------------------------- Tier 2: numeric
def local_csv(osd_id):
    hits = glob.glob(os.path.join(ROOT, "data/raw", f"{osd_id}_*.csv"))
    return hits[0] if hits else None


def local_csv_all():
    return sorted(glob.glob(os.path.join(ROOT, "data/raw", "OSD-*.csv")))


def fetch_dge(osd_id, progress=print):
    """Download a study's differential-expression CSV from OSDR into data/raw (about 20 MB each)."""
    path = local_csv(osd_id)
    if path:
        return path
    row = study(osd_id)
    path = os.path.join(ROOT, "data/raw", f"{osd_id}_differential_expression.csv")
    progress(f"downloading {osd_id}")
    urllib.request.urlretrieve(row["dge_url"], path)
    return path


def numeric_facts(lead, table):
    return {k: table.facts(k) for k in lead.get("rows", [])}


def _direction(f):
    """+1 / -1 / 0 (not significant) / None (not measured) for one gene or GO-term fact."""
    if not isinstance(f, dict) or "error" in f:
        return None
    if "log2fc" in f:
        p = f.get("padj")
        if p is None or p != p:                                    # NaN: the pipeline did not test it
            return None
        return (1 if f["log2fc"] > 0 else -1) if p < 0.05 else 0
    if "up" in f:                                                  # GO term: majority direction of significant members
        if f["significant"] == 0:
            return 0
        return 1 if f["up"] >= f["down"] else -1
    return None


def agreement(lead_facts, other_facts):
    """Pure arithmetic: per gene, does the other table point the same way, the opposite way, show no change, or lack it."""
    tally = {"same": 0, "opposite": 0, "no_change": 0, "not_measured": 0}
    for k, f in lead_facts.items():
        d0, d1 = _direction(f), _direction(other_facts.get(k))
        if d0 in (None, 0) or d1 is None:
            tally["not_measured"] += 1
        elif d1 == 0:
            tally["no_change"] += 1
        elif d1 == d0:
            tally["same"] += 1
        else:
            tally["opposite"] += 1
    return tally
