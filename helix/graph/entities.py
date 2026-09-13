"""Nodes of the graph: findings (leads and paper claims) and the entities they and the passages mention.

    findings()                      -> [{id, kind, dataset, claim, genes, go, status, ...}]
    gene_vocab()                    -> {UPPER: display} from the SYMBOL columns of the DGE tables on disk (~25k symbols)
    tag_passages(passages, client)  -> adds passage["genes"], ["tissues"], ["factors"]; Jev confirms ambiguous gene hits

Matching is code (exact symbols, curated tissue/factor vocab). TypeSafe is used only where code cannot decide:
a symbol that is also an English word ("Sag", "Cat", "Mice") gets one Noul per hit: is it the gene here?
"""
import csv, glob, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "data/osdr_catalog.csv")
VOCAB = os.path.join(ROOT, "data/corpus/gene_vocab.json")

# tissue -> regex over passage text (adjective forms included). Keys are the entity ids.
TISSUES = {
    "thymus": r"thym(us|ic|ocyte)", "retina": r"retin(a|al|ae)|photoreceptor", "bone": r"\bbone|skelet|osteo|femur|tibia|cortical bone|trabecul",
    "muscle": r"\bmuscle|soleus|gastrocnemius|tibialis|quadriceps|extensor digitorum|myofib", "liver": r"\bliver|hepat",
    "kidney": r"\bkidney|renal", "skin": r"\bskin\b|dermal|epiderm", "spleen": r"\bspleen|splenic", "eye": r"\beye|ocular|lens\b|cornea",
    "heart": r"\bheart|cardiac|myocard", "brain": r"\bbrain|hippocamp|cortex|neuron", "lung": r"\blung|pulmonary",
    "adrenal": r"adrenal", "bone marrow": r"bone marrow|hematopoietic", "blood": r"\bblood\b|plasma|serum|leukocyte|lymphocyte|PBMC",
    "intestine": r"intestin|colon\b|gut\b", "mammary": r"mammary", "testis": r"testis|testes", "plant": r"arabidopsis|seedling|root tip|hypocotyl",
}
FACTORS = {
    "spaceflight": r"space ?flight|spaceflown|space-flown|in space\b|ISS\b|international space station|shuttle|space mission|orbit",
    "microgravity": r"micro-?gravity|microgravity|weightless|\bµg\b|\buG\b", "hindlimb unloading": r"hindlimb[ -]unload|hind-?limb suspension|\bHLU\b|\bHU\b",
    "radiation": r"radiation|irradiat|\bGCR\b|cosmic ray|proton|\bHZE\b|56Fe", "altered gravity": r"hypergravity|centrifug|partial gravity|artificial gravity|1 ?g control",
    "simulated microgravity": r"simulated micro-?gravity|clinostat|random positioning|rotating wall|\bRWV\b|bed rest|head-down tilt",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,14}")


# ---------------------------------------------------------------- findings
def _label_index():
    labs = {}
    for f in glob.glob(os.path.join(ROOT, "data/golden/labels*.jsonl")):
        for line in open(f):
            r = json.loads(line); labs[r.get("lead_id") or r.get("id")] = r.get("label")
    return labs


def findings():
    """Every finding the project has produced or checked, deduplicated by id.
    kind: 'survivor' / 'killed' (product runs), 'lead' (ledger, with its golden label), 'paper_claim' (NASA papers)."""
    out, seen = [], set()

    def add(lead, kind, status):
        if lead["id"] in seen:
            return
        seen.add(lead["id"])
        rows = lead.get("rows", [])
        out.append({"id": lead["id"], "kind": kind, "status": status, "dataset": lead["dataset"], "shape": lead.get("shape", ""),
                    "claim": lead["claim"], "genes": [r for r in rows if not r.startswith("GO:")], "go": [r for r in rows if r.startswith("GO:")],
                    "why_not_known": lead.get("why_not_known", ""), "next_step": lead.get("next_step", ""),
                    "table_facts": lead.get("table_facts", {}), "reason": lead.get("reason", lead.get("label_note", "")),
                    "paper": lead.get("paper"), "group": lead.get("group")})

    for f in sorted(glob.glob(os.path.join(ROOT, "results/product_*.json"))):
        d = json.load(open(f))
        for s in d["survivors"]:
            add(s, "survivor", "ok")
        for k in d["killed"]:
            add(k, "killed", k["label"])
    for f in sorted(glob.glob(os.path.join(ROOT, "data/golden/nasa_OSD-*.json"))):
        if "numbered" in f:
            continue
        for c in json.load(open(f)):
            add(c, "paper_claim", c.get("label", ""))
    labs = _label_index()
    for l in json.load(open(os.path.join(ROOT, "ledger/leads_all_enriched.json"))):
        add(l, "lead", labs.get(l["id"], ""))
    return out


# ---------------------------------------------------------------- vocabularies
def gene_vocab():
    """UPPER -> display symbol, from every DGE table on disk. Cached; delete data/corpus/gene_vocab.json to rebuild."""
    if os.path.exists(VOCAB):
        return json.load(open(VOCAB))
    import pandas as pd
    vocab = {}
    for p in glob.glob(os.path.join(ROOT, "data/raw/OSD-*.csv")):
        for s in pd.read_csv(p, usecols=["SYMBOL"], low_memory=False)["SYMBOL"].dropna().astype(str):
            if 3 <= len(s) <= 15 and re.match(r"^[A-Za-z][A-Za-z0-9\-]+$", s) and not s.startswith(("Gm", "LOC")) and "Rik" not in s:
                vocab.setdefault(s.upper(), s)
    json.dump(vocab, open(VOCAB, "w"))
    return vocab


def english_words():
    try:
        return {w.strip().lower() for w in open("/usr/share/dict/words") if len(w.strip()) >= 3}
    except FileNotFoundError:
        return set()


def catalog_tissue(osd_id):
    """Entity ids for a catalog study's material, via the same regexes used on passages."""
    row = next((r for r in csv.DictReader(open(CATALOG)) if r["osd_id"] == osd_id), None)
    if not row:
        return [], []
    text = row["material"] + " " + row["factors"]
    return ([t for t, rx in TISSUES.items() if re.search(rx, text, re.I)],
            [f for f, rx in FACTORS.items() if re.search(rx, text, re.I)])
