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


# ---------------------------------------------------------------- PubMed + PMC
def _text(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def fetch_papers(studies, fulltext=True, progress=print):
    """pmid -> {title, abstract, pmcid, sections:[{title, paragraphs}], osd_ids}. Cached."""
    path = os.path.join(DIR, "papers.json")
    papers = json.load(open(path)) if os.path.exists(path) else {}
    by_pmid = {}
    for osd, s in studies.items():
        for p in s["publications"]:
            by_pmid.setdefault(p["pmid"], {"doi": p["doi"], "osd_ids": []})["osd_ids"].append(osd)
    for pmid, meta in by_pmid.items():
        papers.setdefault(pmid, {})["osd_ids"] = sorted(set(meta["osd_ids"]))
        papers[pmid]["doi"] = meta["doi"]
    todo = [p for p in by_pmid if "abstract" not in papers[p]]
    for i in range(0, len(todo), 50):                                  # abstracts, 50 per call
        batch = todo[i:i + 50]
        root = ET.fromstring(_eutils("efetch.fcgi", db="pubmed", id=",".join(batch), retmode="xml"))
        for art in root.iter("PubmedArticle"):
            pmid = _text(art.find(".//PMID"))
            if pmid not in papers:
                continue
            abstract = " ".join(((a.get("Label") + ": ") if a.get("Label") else "") + _text(a) for a in art.findall(".//AbstractText"))
            papers[pmid].update({"title": _text(art.find(".//ArticleTitle")), "abstract": abstract,
                                 "journal": _text(art.find(".//Journal/Title")), "year": _text(art.find(".//PubDate/Year"))})
        for pmid in batch:
            papers[pmid].setdefault("abstract", ""); papers[pmid].setdefault("title", "")
        progress(f"  abstracts {min(i+50, len(todo))}/{len(todo)}")
    if fulltext:
        need = [p for p in papers if "pmcid" not in papers[p]]
        for i in range(0, len(need), 100):                             # pubmed -> pmc ids
            batch = need[i:i + 100]
            root = ET.fromstring(_eutils("elink.fcgi", dbfrom="pubmed", db="pmc", id=batch, retmode="xml"))   # one LinkSet per id
            for ls in root.iter("LinkSet"):
                pmid = _text(ls.find("IdList/Id"))
                link = ls.find(".//LinkSetDb[DbTo='pmc']/Link/Id")
                if pmid in papers:
                    papers[pmid]["pmcid"] = _text(link) if link is not None else ""
            for pmid in batch:
                papers[pmid].setdefault("pmcid", "")
        need = [p for p in papers if papers[p].get("pmcid") and "sections" not in papers[p]]
        for j, pmid in enumerate(need):                                # full text, one call per paper
            try:
                root = ET.fromstring(_eutils("efetch.fcgi", db="pmc", id=papers[pmid]["pmcid"], retmode="xml"))
                secs = []
                for sec in root.iter("sec"):
                    if sec.find("sec") is not None:                       # keep leaves only: a section with subsections repeats them
                        continue
                    title = _text(sec.find("title"))
                    paras = [_text(p) for p in sec.findall("p")]
                    paras = [re.sub(r"\s+", " ", p) for p in paras if len(p.split()) >= 12]
                    if paras and not re.match(r"(?i)^(references|acknowledg|author contributions|competing|funding|supplementary|data availability|abbreviations|ethics)", title):
                        secs.append({"title": title, "paragraphs": paras})
                papers[pmid]["sections"] = secs                           # [] when PMC returns only front matter (not OA)
            except Exception as e:
                papers[pmid]["sections"] = []; papers[pmid]["fulltext_error"] = f"{type(e).__name__}"[:60]
            if j % 10 == 9:
                progress(f"  full text {j+1}/{len(need)}"); json.dump(papers, open(path, "w"), indent=1)
    json.dump(papers, open(path, "w"), indent=1)
    n_ft = sum(1 for p in papers.values() if p.get("sections"))
    progress(f"{len(papers)} papers, {sum(1 for p in papers.values() if p.get('abstract'))} abstracts, {n_ft} with open-access full text")
    return papers


# ---------------------------------------------------------------- passages
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")


def chunk(text, max_words=MAX_WORDS):
    """Sentence-bounded chunks of at most max_words; a lone long sentence stays whole."""
    out, cur = [], []
    for s in _SENT.split(text.strip()):
        if cur and len(" ".join(cur + [s]).split()) > max_words:
            out.append(" ".join(cur)); cur = []
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return [c for c in out if len(c.split()) >= 6]


def build_passages(studies, papers, progress=print):
    """passages.jsonl: {id, source: 'osdr'|'abstract'|'fulltext', pmid, osd_ids, section, text}."""
    path = os.path.join(DIR, "passages.jsonl")
    rows = []
    for osd, s in studies.items():
        for k, c in enumerate(chunk(s["description"])):
            rows.append({"id": f"{osd}:desc:{k}", "source": "osdr", "pmid": "", "osd_ids": [osd], "section": "study description", "text": c})
    for pmid, p in papers.items():
        for k, c in enumerate(chunk(p.get("abstract", ""))):
            rows.append({"id": f"pmid{pmid}:abs:{k}", "source": "abstract", "pmid": pmid, "osd_ids": p["osd_ids"], "section": "abstract", "text": c})
        for si, sec in enumerate(p.get("sections", [])):
            for pi, para in enumerate(sec["paragraphs"]):
                for k, c in enumerate(chunk(para)):
                    rows.append({"id": f"pmid{pmid}:s{si}p{pi}:{k}", "source": "fulltext", "pmid": pmid, "osd_ids": p["osd_ids"],
                                 "section": sec["title"] or "body", "text": c})
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1
    progress(f"{len(rows)} passages: {by}")
    return rows


def load_passages():
    return [json.loads(l) for l in open(os.path.join(DIR, "passages.jsonl"))]


def build(fulltext=True, progress=print):
    os.makedirs(DIR, exist_ok=True)
    studies = fetch_studies(progress)
    papers = fetch_papers(studies, fulltext=fulltext, progress=progress)
    return studies, papers, build_passages(studies, papers, progress)


if __name__ == "__main__":
    build(fulltext="--no-fulltext" not in sys.argv)
