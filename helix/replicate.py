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


def _slim(facts):
    """The numbers Jev needs, without per-sample lists (request size)."""
    return {k: ({x: f[x] for x in ("log2fc", "padj", "higher_group", "carriers", "mean_count", "error",
                                    "significant", "up", "down", "enrichment_vs_baseline") if x in f}
                if isinstance(f, dict) else f) for k, f in facts.items()}


TIER2_CHUNK = 3                  # other datasets per request; family leads carry many genes


def replication_verdicts(lead, own, others, client):
    """others: [(osd_id, meta, facts, comparable_level)] for tables already looked up. One Choice per other dataset,
    TIER2_CHUNK datasets per request. Jev sees the code-computed agreement tally and the Tier-1 comparability; the gate is code."""
    out = []
    for i in range(0, len(others), TIER2_CHUNK):
        out += _replication_chunk(lead, own, others[i:i + TIER2_CHUNK], client)
    return out


def _gate(answer, tally, level):
    """Code policy over Jev's distribution: an unrelated tissue is always inconclusive; 'replicated' needs a significant
    same-direction gene and 'contradicted' a significant opposite one. Otherwise take Jev's most probable admissible choice."""
    if level < 2:
        return "inconclusive"
    banned = ({"replicated"} if not tally["same"] else set()) | ({"contradicted"} if not tally["opposite"] else set())
    if answer.choice not in banned:
        return answer.choice
    return max((c for c in REPLICATION if c not in banned), key=lambda c: answer.probabilities.get(c, 0.0))


def _replication_chunk(lead, own, others, client):
    from typesafe_sdk import Choice
    if not others:
        return []
    tallies = [agreement(lead.get("table_facts", {}), facts) for _, _, facts, _ in others]
    state = {"lead": _lead_state(lead, own), "lead_facts": _slim(lead.get("table_facts", {})),
             "others": [{"osd_id": oid, **{k: m[k] for k in ("material", "factors", "assay")}, "facts": _slim(facts),
                         "agreement_by_gene": t, "comparability": COMPARABLE[round(lvl)]}
                        for (oid, m, facts, lvl), t in zip(others, tallies)]}
    qs = {f"o{j}": Choice(
        instructions=f"`lead` was found in `lead.dataset` with the numbers in `lead_facts`. `others[{j}].facts` are the same "
                     f"genes looked up in dataset `others[{j}].osd_id`; `others[{j}].agreement_by_gene` counts, per gene, whether "
                     f"that dataset points the same way, the opposite way, shows no change, or did not measure it; "
                     f"`others[{j}].comparability` says how comparable its tissue and factor are. What does that dataset say about the lead?",
        criteria=REPLICATION) for j in range(len(others))}
    r = client.system_one(state=state, questions=qs)
    out = []
    for j, (oid, m, facts, lvl) in enumerate(others):
        a = r.answers[f"o{j}"]
        verdict = _gate(a, tallies[j], lvl)
        out.append({"osd_id": oid, "material": m["material"], "factors": m["factors"], "verdict": verdict, "jev_verdict": a.choice,
                    "comparable": round(lvl, 2), "agreement": tallies[j],
                    "p_replicated": round(a.probabilities.get("replicated", 0.0), 2),
                    "p_contradicted": round(a.probabilities.get("contradicted", 0.0), 2),
                    "confidence": round(a.confidence, 2), "facts": facts})
    return out


def overall(numeric, where):
    """Code rule, not a model: contradiction > replication > not replicated > untested > novel."""
    v = {n["osd_id"]: n["verdict"] for n in numeric}
    if any(x == "contradicted" for x in v.values()):
        return "contradicted by " + ", ".join(k for k, x in v.items() if x == "contradicted")
    if any(x == "replicated" for x in v.values()):
        return "replicated in " + ", ".join(k for k, x in v.items() if x == "replicated")
    if any(x == "not_replicated" for x in v.values()):
        return "not replicated in " + ", ".join(k for k, x in v.items() if x == "not_replicated")
    direct = [w["osd_id"] for w in where if w["comparable"] >= 2.5 and not w["on_disk"]]
    if direct:
        return f"untested: {len(direct)} comparable dataset(s) not on disk ({', '.join(direct[:3])})"
    return "novel as far as OSDR goes: no comparable dataset contradicts or replicates it"


# ---------------------------------------------------------------- driver
def check_novelty(product_json, max_studies=None, progress=print, client=None, dry_run=False):
    t0 = time.time()
    prod = json.load(open(product_json))
    own = study(prod["dataset"])
    organism = own["organism"].replace("Not Applicable | ", "")
    studies = [r for r in catalog() if organism in r["organism"] and r["osd_id"] != prod["dataset"]]
    others = [(os.path.basename(p).split("_")[0], p) for p in sorted(glob.glob(os.path.join(ROOT, "data/raw/OSD-*.csv")))
              if not os.path.basename(p).startswith(prod["dataset"] + "_")]
    if max_studies:                                   # keep the on-disk ones: Tier 2 needs their comparability
        keep = {o for o, _ in others}
        studies = [r for r in studies if r["osd_id"] in keep] + [r for r in studies if r["osd_id"] not in keep][:max_studies]
    progress(f"{len(prod['survivors'])} survivors x {len(studies)} {organism} studies; {len(others)} other tables on disk")
    tables = {oid: Table(p) for oid, p in others}
    client = client or (None if dry_run else _client())

    def one(lead):
        if dry_run:
            where = [{**_meta(r), "comparable": 0, "p_direct": 0, "confidence": 0, "same_factor": 0, "on_disk": bool(local_csv(r["osd_id"]))} for r in studies[:5]]
            numeric = [{"osd_id": oid, "material": study(oid)["material"], "factors": study(oid)["factors"], "verdict": "inconclusive",
                        "jev_verdict": "inconclusive", "comparable": 0, "agreement": agreement(lead.get("table_facts", {}), numeric_facts(lead, t)),
                        "p_replicated": 0, "p_contradicted": 0, "confidence": 0, "facts": numeric_facts(lead, t)} for oid, t in tables.items()]
        else:
            where = catalog_scores(lead, own, studies, client)
            level = {w["osd_id"]: w["comparable"] for w in where}
            looked = [(oid, study(oid), numeric_facts(lead, t), level.get(oid, 0)) for oid, t in tables.items()]
            looked = [(oid, m, f, l) for oid, m, f, l in looked if f and not all("error" in x for x in f.values())]
            numeric = replication_verdicts(lead, own, looked, client)
        return {"id": lead["id"], "shape": lead["shape"], "claim": lead["claim"], "genes": lead.get("rows", []),
                "why_not_known": lead.get("why_not_known", ""), "where_to_look": where[:12], "numeric": numeric,
                "n_comparable": sum(w["comparable"] >= 2.5 for w in where),
                "verdict": overall(numeric, where)}

    done = []
    with ThreadPoolExecutor(WORKERS) as ex:
        for res in ex.map(one, prod["survivors"]):
            done.append(res); progress(f"  {res['id']}: {res['verdict']}")
    out = {"dataset": prod["dataset"], "organism": organism, "n_studies": len(studies), "tables_on_disk": [o for o, _ in others],
           "leads": done, "seconds": round(time.time() - t0)}
    path = os.path.join(ROOT, "results", f"replicate_{prod['dataset']}.json")
    json.dump(out, open(path, "w"), indent=1)
    progress(f"done in {out['seconds']} s -> {path}")
    return out


if __name__ == "__main__":
    out = check_novelty(sys.argv[1], max_studies=int(sys.argv[2]) if len(sys.argv) > 2 else None)
    from collections import Counter
    print(Counter(l["verdict"].split(":")[0].split(" in ")[0].split(" by ")[0] for l in out["leads"]))
