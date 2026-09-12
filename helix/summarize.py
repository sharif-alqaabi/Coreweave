"""Boil a processed OSDR differential-expression CSV down to a ~600-token summary
that supports several lead shapes: single gene, robust gene, family, pathway,
global pattern, and data quality.

    python3 helix/summarize.py data/raw/OSD-104_rna_seq_differential_expression.csv
"""
import json, re, sys, urllib.request
from collections import Counter, defaultdict
import pandas as pd

GO_CACHE = "data/go_names.json"
TAG = {"Space Flight": "_FLT_", "Ground Control": "_GC_"}   # OSD sample-name codes


def load(path):
    """Return the table plus the column names that describe the flight-vs-ground contrast."""
    df = pd.read_csv(path, low_memory=False)
    lfcs = [c for c in df.columns if c.startswith("Log2fc_(")]
    lfc = next((c for c in lfcs if c.startswith("Log2fc_(Space Flight)")), lfcs[0])
    padj = "Adj.p.value_" + lfc[len("Log2fc_"):]
    a, b = re.match(r"Log2fc_\((.*)\)v\((.*)\)", lfc).groups()
    first_stat = list(df.columns).index(lfcs[0])
    samples = [c for c in df.columns[:first_stat] if df[c].dtype != object and c != "ENTREZID"]
    grp = {a: [c for c in samples if TAG.get(a, a) in c],
           b: [c for c in samples if TAG.get(b, b) in c]}
    return df, lfc, padj, a, b, grp


def gene_line(r, lfc, padj, a, b, grp):
    """One summary line per gene, with facts an LLM cannot compute itself."""
    hi = a if r[lfc] > 0 else b
    carriers = int((r[grp[hi]] > 1).sum())
    mean_hi = r[grp[hi]].mean()
    return (f"- {r['SYMBOL']}: log2fc={r[lfc]:+.2f}, padj={r[padj]:.1e}, "
            f"carriers={carriers}/{len(grp[hi])}, mean_count_in_{'FLT' if hi == a else 'GC'}={mean_hi:.0f}; "
            f"{str(r['GENENAME'])[:38]}")


def families(sig, lfc, min_size=3, pool=150):
    """Gene families among the top hits, by symbol prefix (Krt17, Krt14 -> Krt)."""
    top = sig.reindex(sig[lfc].abs().sort_values(ascending=False).index).head(pool)
    fam = defaultdict(list)
    for _, r in top.iterrows():
        m = re.match(r"[A-Za-z]+", str(r["SYMBOL"]))
        if m and len(m.group()) >= 2:
            fam[m.group()].append(r)
    lines = []
    for name, rows in sorted(fam.items(), key=lambda kv: -len(kv[1])):
        if len(rows) < min_size:
            break
        up = sum(r[lfc] > 0 for r in rows)
        syms = ", ".join(r["SYMBOL"] for r in rows[:6])
        lines.append(f"- {name}* ({len(rows)} genes in top {pool}; {up} up, {len(rows)-up} down): {syms}")
    return lines


def go_names(ids):
    """GO id -> name via EBI QuickGO, cached on disk so it runs once."""
    try:
        cache = json.load(open(GO_CACHE))
    except FileNotFoundError:
        cache = {}
    missing = [i for i in ids if i not in cache]
    if missing:
        try:
            url = "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/" + ",".join(missing)
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            for r in json.load(urllib.request.urlopen(req, timeout=30))["results"]:
                cache[r["id"]] = r["name"]
            json.dump(cache, open(GO_CACHE, "w"), indent=0)
        except Exception:
            pass                                   # offline: fall back to raw ids
    return {i: cache.get(i, i) for i in ids}


def pathways(df, sig, lfc, min_genes=30, top=8):
    """GO-slim terms where significant genes are over-represented vs the whole table."""
    def terms(s): return str(s).split("|") if isinstance(s, str) else []
    all_ct = Counter(t for s in df["GOSLIM_IDS"] for t in terms(s))
    sig_up = Counter(t for s in sig[sig[lfc] > 0]["GOSLIM_IDS"] for t in terms(s))
    sig_dn = Counter(t for s in sig[sig[lfc] < 0]["GOSLIM_IDS"] for t in terms(s))
    base = len(sig) / len(df)
    rows = []
    for t, n in all_ct.items():
        k = sig_up[t] + sig_dn[t]
        if n >= min_genes and k:
            rows.append((k / n / base, t, k, n, sig_up[t], sig_dn[t]))
    rows.sort(reverse=True)
    names = go_names([t for _, t, *_ in rows[:top]])
    return [f"- {names[t]} ({t}): {k}/{n} genes significant ({ratio:.1f}x baseline; {up} up, {dn} down)"
            for ratio, t, k, n, up, dn in rows[:top]]


def sample_flags(sig, lfc, grp, a, b, pool=50):
    """Samples that alone carry many top genes: a contamination / outlier warning."""
    top = sig.reindex(sig[lfc].abs().sort_values(ascending=False).index).head(pool)
    lone = Counter()
    for _, r in top.iterrows():
        cols = grp[a] if r[lfc] > 0 else grp[b]
        on = [c for c in cols if r[c] > 1]
        if len(on) <= 2:
            lone.update(on)
    flagged = [(c.split("_")[-1], n) for c, n in lone.most_common() if n >= 3]
    if not flagged:
        return ["- none: top genes are carried by most samples in their group"]
    return [f"- sample {s} is one of <=2 carriers for {n} of the top {pool} genes" for s, n in flagged]


def significant(df, padj, alpha=0.05):
    return df[(df[padj] < alpha) & df["SYMBOL"].notna() & (df["SYMBOL"] != "NA")]


def header(name, df, sig, lfc, a, b, grp, alpha=0.05):
    """Four lines describing the whole experiment; reused in every critic payload."""
    big = sig[sig[lfc].abs() > 1]
    return [f"Dataset: {name}",
            f"Contrast: {a} vs {b}; +log2fc = higher in {a}. n={len(grp[a])} {a}, n={len(grp[b])} {b}.",
            f"Genes tested: {len(df)}. Significant at FDR<{alpha}: {len(sig)} "
            f"({(sig[lfc] > 0).sum()} up, {(sig[lfc] < 0).sum()} down); "
            f"{len(big)} of those change >=2-fold ({(big[lfc] > 0).sum()} up, {(big[lfc] < 0).sum()} down).",
            f"Median |log2fc| among significant genes: {sig[lfc].abs().median():.2f}."]


def go_term_facts(df, sig, lfc, term):
    """Enrichment facts for one GO id, so pathway leads can be checked."""
    has = lambda s: isinstance(s, str) and term in s.split("|")
    n = int(df["GOSLIM_IDS"].map(has).sum())
    hit = sig[sig["GOSLIM_IDS"].map(has)]
    base = len(sig) / len(df)
    return {"name": go_names([term])[term], "genes_in_term": n, "significant": len(hit),
            "up": int((hit[lfc] > 0).sum()), "down": int((hit[lfc] < 0).sum()),
            "enrichment_vs_baseline": round(len(hit) / n / base, 2) if n else None}


def summarize(path, alpha=0.05, n_lfc=25, n_padj=12):
    df, lfc, padj, a, b, grp = load(path)
    sig = significant(df, padj, alpha)
    out = header(path.split("/")[-1], df, sig, lfc, a, b, grp, alpha)
    out += ["", f"## Top {n_lfc} by fold change (carriers = samples in the higher group with count > 1)"]
    by_lfc = sig.reindex(sig[lfc].abs().sort_values(ascending=False).index).head(n_lfc)
    out += [gene_line(r, lfc, padj, a, b, grp) for _, r in by_lfc.iterrows()]
    out += ["", f"## Top {n_padj} by confidence (smallest padj, not already listed)"]
    by_p = sig[~sig.index.isin(by_lfc.index)].sort_values(padj).head(n_padj)
    out += [gene_line(r, lfc, padj, a, b, grp) for _, r in by_p.iterrows()]
    out += ["", "## Borderline (0.05 <= padj < 0.25) and null (padj > 0.5) examples, for calibration"]
    named = df[df["SYMBOL"].notna() & (df["SYMBOL"] != "NA") & df[padj].notna()]
    border = named[(named[padj] >= alpha) & (named[padj] < 0.25)]
    border = border.reindex(border[lfc].abs().sort_values(ascending=False).index).head(5)
    null = named[named[padj] > 0.5].sample(5, random_state=0)
    out += [gene_line(r, lfc, padj, a, b, grp) for _, r in pd.concat([border, null]).iterrows()]
    out += ["", "## Gene families among top hits"] + families(sig, lfc)
    out += ["", "## Pathways (GO-slim) enriched among significant genes"] + pathways(df, sig, lfc)
    out += ["", "## Sample-quality flags"] + sample_flags(sig, lfc, grp, a, b)
    return "\n".join(out)


if __name__ == "__main__":
    print(summarize(sys.argv[1]))
