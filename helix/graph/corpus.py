"""The text corpus behind the graph: for every OSDR study in the catalog, the study description and the
publications OSDR links to it (PubMed abstract; PMC full text when open access), cut into passages.

    python -m helix.graph.corpus            # builds data/corpus/{studies,papers}.json and passages.jsonl (cached)

Sources: OSDR meta API (study -> publications with PubMed ids), NCBI E-utilities (efetch pubmed/pmc, elink pubmed->pmc).
NCBI allows 3 requests/s without a key; this stays under that.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "data/osdr_catalog.csv")
DIR = os.path.join(ROOT, "data/corpus")
OSDR = "https://osdr.nasa.gov/osdr/data/osd/meta/{}"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL = {"tool": "helix-graph", "email": os.getenv("NCBI_EMAIL", "")}
MAX_WORDS = 110                 # passage size: a few sentences, enough to state one finding with its numbers


def _get(url, retries=3, sleep=0.34):
    for i in range(retries):
        try:
            time.sleep(sleep)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "helix-graph/0.1"}), timeout=60) as r:
                return r.read()
        except Exception as e:                                       # NCBI 429s and OSDR hiccups: back off
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def _eutils(endpoint, **params):
    q = urllib.parse.urlencode({**TOOL, **params}, doseq=True)      # a list value repeats the key (elink needs id=..&id=..)
    return _get(EUTILS + endpoint + "?" + q)


# ---------------------------------------------------------------- OSDR studies
def fetch_studies(progress=print):
    """osd_id -> {title, description, publications:[{pmid, doi, title}]} for every catalog row. Cached."""
    path = os.path.join(DIR, "studies.json")
    studies = json.load(open(path)) if os.path.exists(path) else {}
    rows = list(csv.DictReader(open(CATALOG)))
    todo = [r["osd_id"] for r in rows if r["osd_id"] not in studies]
    for i, osd in enumerate(todo):
        try:
            d = json.loads(_get(OSDR.format(osd.split("-")[1]), sleep=0.1))
            st = d["study"][osd]["studies"][0]
            pubs = [{"pmid": str(p.get("pubMedID") or "").strip(), "doi": p.get("doi", ""), "title": p.get("title", "")}
                    for p in st.get("publications", [])]
            studies[osd] = {"title": st.get("title", ""), "description": st.get("description", ""),
                            "publications": [p for p in pubs if p["pmid"]]}
        except Exception as e:
            studies[osd] = {"title": "", "description": "", "publications": [], "error": f"{type(e).__name__}: {e}"[:120]}
        if i % 20 == 19:
            progress(f"  studies {i+1}/{len(todo)}"); json.dump(studies, open(path, "w"), indent=1)
    json.dump(studies, open(path, "w"), indent=1)
    n_pub = sum(len(s["publications"]) for s in studies.values())
    progress(f"{len(studies)} studies, {n_pub} linked publications")
    return studies
