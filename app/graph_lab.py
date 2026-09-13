"""Graph Lab: explore the research knowledge graph. Run:  marimo run app/graph_lab.py

Nodes: findings (scout leads, product survivors, NASA paper claims), passages, papers, datasets, genes, GO terms, tissues.
Edges: judged by TypeSafe (Jev) with probabilities; explained by a regular LLM on demand. Built by `python -m helix.graph.build`.
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo, os, sys, json, re, time
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
    sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv(".env")
    from helix.graph import explain as EX, corpus as C
    return mo, os, json, re, time, ROOT, EX, C


@app.cell
def _(mo):
    rebuild = mo.ui.run_button(label="Rebuild graph (TypeSafe, about 2 min)", kind="neutral")
    mo.vstack([
        mo.md("# Research Graph Lab"),
        mo.md("Every finding this project produced or checked (scout leads, product survivors, NASA paper claims), linked to the passages "
              "that support, contradict or explain them across **150 papers and 243 OSDR studies**, and to each other. "
              "**TypeSafe (Jev)** does the finding: a relevance rerank over a broad passage pool, then a typed relationship judgment "
              "per pair, ~10,000 pairs in 90 s, each edge carrying its probabilities. Direction and significance are arithmetic in pandas. "
              "A regular LLM only writes the one-sentence explanation of links already accepted."),
        rebuild,
    ])
    return (rebuild,)


@app.cell
def _(mo, rebuild, json, os):
    if rebuild.value:
        import subprocess, sys as _sys
        with mo.status.spinner(title="Building: corpus (cached), entity tagging, TypeSafe judgments, assembly"):
            r = subprocess.run([_sys.executable, "-m", "helix.graph.build", "--no-explain"], capture_output=True, text=True)
        build_note = mo.md(f"```\n{(r.stdout or r.stderr)[-1200:]}\n```")
    else:
        build_note = None
    graph = json.load(open("results/graph.json")) if os.path.exists("results/graph.json") else None
    build_note
    return (graph,)


@app.cell
def _(mo, graph):
    if graph is None:
        mo.stop(True, mo.md("_No graph yet. Press **Rebuild graph** or run `python -m helix.graph.build`._"))
    N = {n["id"]: n for n in graph["nodes"]}
    st = graph["stats"]
    _counts = {k: v for k, v in st["edges"].items() if k.split(":")[0] in ("finding-passage", "finding-finding") or k.startswith("finding-dataset:") and not k.endswith(":from")}
    mo.md(f"## Built {graph['built']}: **{st['nodes']['finding']} findings**, {st['nodes'].get('passage', 0)} passages from "
          f"{st['nodes'].get('paper', 0)} papers, {st['nodes'].get('dataset', 0)} datasets, {st['nodes'].get('gene', 0)} genes; "
          f"**{sum(_counts.values())} judged edges kept** of {sum(_counts.values()) + st['judged_dropped']} pairs scored, in {st['seconds']} s  \n"
          + "  ".join(f"`{k.split(':')[1]}` {v}" for k, v in sorted(_counts.items(), key=lambda kv: -kv[1])))
    return (N,)


@app.cell
def _(mo):
    min_conf = mo.ui.slider(0.0, 1.0, value=0.5, step=0.05, label="min confidence")
    min_sup = mo.ui.slider(0.0, 1.0, value=0.0, step=0.05, label="min P(supports) for passage links")
    kinds = mo.ui.multiselect(options=["supports", "consistent", "contradicts", "background", "rediscovers", "restates", "replicates",
                                       "extends", "same_entity_different_claim", "replicated", "contradicted", "not_replicated", "underpowered"],
                              value=["supports", "consistent", "contradicts", "background", "rediscovers", "replicates", "extends", "replicated", "contradicted", "not_replicated"],
                              label="relations shown")
    mo.hstack([min_conf, min_sup, kinds], justify="start")
    return min_conf, min_sup, kinds


@app.cell
def _(graph, N, min_conf, min_sup, kinds):
    # Thresholds are policy over stored probabilities: moving a slider never reruns a model.
    def visible(e):
        if e["relation"] not in kinds.value:
            return False
        if e["type"] == "finding-passage":
            return e["confidence"] >= min_conf.value and e["p_supports"] >= (min_sup.value if e["relation"] in ("supports", "consistent") else 0)
        if e["type"] == "finding-finding":
            return e["confidence"] >= min_conf.value
        return True
    judged = [e for e in graph["edges"] if e["type"] in ("finding-passage", "finding-finding") or (e["type"] == "finding-dataset" and e["relation"] != "from")]
    shown_edges = [e for e in judged if visible(e)]
    return shown_edges, judged


@app.cell
def _(mo, N, shown_edges):
    # The three tables a scientist opens first.
    def claim(i): return N[i]["claim"][:95]
    contra = [{"finding": e["src"], "claim": claim(e["src"]), "status": N[e["src"]]["status"], "P(contradicts)": e.get("p_contradicts"),
               "passage": N[e["dst"]]["text"][:220], "paper": N["pmid" + N[e["dst"]]["pmid"]]["title"][:60] if N[e["dst"]]["pmid"] else "OSDR description",
               "explanation": e.get("explanation", "")} for e in shown_edges if e["type"] == "finding-passage" and e["relation"] == "contradicts"]
    redis = [{"scout lead": e["src"] if N[e["src"]]["kind"] != "paper_claim" else e["dst"], "claim": claim(e["src"]),
              "paper claim": e["dst"] if N[e["dst"]]["kind"] == "paper_claim" else e["src"], "confidence": e["confidence"], "P(same mechanism)": e["p_mechanism"]}
             for e in shown_edges if e["relation"] == "rediscovers" and N[e["src"]]["kind"] != "paper_claim"]
    numeric = [{"finding": e["src"], "claim": claim(e["src"]), "dataset": e["dst"], "verdict": e["relation"], "comparable": e["comparable"],
                **e["agreement"], "numbers": "; ".join(f"{g}: log2fc {v['log2fc']}, padj {v['padj']:.2g}" for g, v in list(e["numbers"].items())[:3])}
               for e in shown_edges if e["type"] == "finding-dataset" and e["relation"] in ("replicated", "contradicted")]
    mo.vstack([
        mo.md(f"### Contradicted by the literature: {len(contra)} links"),
        mo.md("_A passage that reports the opposite direction, or explicitly no change, for the finding's gene. P(contradicts) is Jev's dedicated judgment; the relation choice is gated on it._"),
        mo.ui.table(contra, selection=None, page_size=8) if contra else mo.md("_none at these thresholds_"),
        mo.md(f"### Rediscoveries: {len(redis)} scout leads that match a published claim"),
        mo.ui.table(redis, selection=None, page_size=8) if redis else mo.md("_none_"),
        mo.md(f"### Replicated or contradicted by another dataset's numbers: {len(numeric)} links"),
        mo.md("_pandas looks the genes up in every comparable table on disk; Jev judges what the numbers mean given the tissue; the verdict is gated by the per-gene tally._"),
        mo.ui.table(numeric, selection=None, page_size=8) if numeric else mo.md("_none_"),
    ])
    return


@app.cell
def _(mo, graph, N):
    findings = [n for n in graph["nodes"] if n["type"] == "finding"]
    opts = {f"{n['id']}  [{n['kind']}/{n['status']}]  {n['claim'][:70]}": n["id"] for n in findings}
    pick = mo.ui.dropdown(options=opts, value=next(iter(opts)), label="Finding", searchable=True)
    gene_opts = sorted(N[g]["label"] for g in N if g.startswith("gene:"))
    gene_pick = mo.ui.dropdown(options=["(any)"] + gene_opts, value="(any)", label="or jump to a gene", searchable=True)
    mo.vstack([mo.md("---\n## Explore one finding"), mo.hstack([pick, gene_pick], justify="start")])
    return pick, gene_pick


@app.cell
def _(mo, graph, N, pick, gene_pick, shown_edges):
    # Gene jump: list the findings that cite it, then use the dropdown to open one.
    fid = pick.value
    if gene_pick.value != "(any)":
        gid = "gene:" + gene_pick.value.upper()
        cites = [e["src"] for e in graph["edges"] if e["type"] == "finding-gene" and e["dst"] == gid]
        mentions = [e["src"] for e in graph["edges"] if e["type"] == "passage-gene" and e["dst"] == gid]
        gene_note = mo.md(f"**{gene_pick.value}**: cited by {len(cites)} findings ({', '.join(cites[:8])}{'...' if len(cites) > 8 else ''}), "
                          f"named in {len(mentions)} linked passages.")
        if cites:
            fid = cites[0] if fid not in cites else fid
    else:
        gene_note = None
    f = N[fid]
    ego = [e for e in shown_edges if e["src"] == fid or e["dst"] == fid]
    gene_note
    return fid, f, ego


@app.cell
def _(mo, N, f, ego, re):
    # Finding card + mermaid ego graph (capped for legibility) + edge table with the passages.
    def sid(x): return re.sub(r"[^A-Za-z0-9]", "_", x)
    def lab(x): return x.replace('"', "'")[:60]
    style = {"supports": "-->", "consistent": "-.->", "contradicts": "==>", "background": "-.->", "rediscovers": "==>", "restates": "-->",
             "replicates": "==>", "extends": "-->", "same_entity_different_claim": "-.->", "replicated": "==>", "contradicted": "==>",
             "not_replicated": "-.->", "underpowered": "-.->"}
    order = {"contradicts": 0, "contradicted": 0, "supports": 1, "rediscovers": 1, "replicates": 1, "replicated": 1, "consistent": 2, "extends": 2}
    top = sorted(ego, key=lambda e: (order.get(e["relation"], 3), -e.get("confidence", 0)))[:22]
    lines = ["graph LR", f'  F["{lab(f["claim"])}"]:::finding']
    for e in top:
        other = e["dst"] if e["src"] == f["id"] else e["src"]; _n = N[other]
        text = _n["text"][:70] + "..." if _n["type"] == "passage" else _n["label"]
        lines.append(f'  {sid(other)}["{lab(text)}"]:::{_n["type"]}')
        p = e.get("p_supports") if e["type"] == "finding-passage" else e.get("confidence", e.get("p_replicated", 0))
        lines.append(f'  F {style.get(e["relation"], "-->")}|{e["relation"]} {p:.2f}| {sid(other)}')
    lines += ["  classDef finding fill:#ffe8b0,stroke:#b07a00", "  classDef passage fill:#e6f0ff,stroke:#3060c0",
              "  classDef dataset fill:#e0f5e0,stroke:#2a7a2a"]
    rows = []
    for e in sorted(ego, key=lambda e: (order.get(e["relation"], 3), -e.get("confidence", 0))):
        other = e["dst"] if e["src"] == f["id"] else e["src"]; _n = N[other]
        if _n["type"] == "passage":
            src = N["pmid" + _n["pmid"]]["title"][:50] if _n["pmid"] else f"OSDR {', '.join(_n['osd_ids'])}"
            rows.append({"relation": e["relation"], "P(supports)": e["p_supports"], "P(contradicts)": e.get("p_contradicts"), "confidence": e["confidence"],
                         "text": _n["text"], "where": f"{src} / {_n['section']}", "explanation": e.get("explanation", ""), "quote": e.get("quote", "")})
        elif _n["type"] == "finding":
            rows.append({"relation": e["relation"], "P(supports)": None, "P(contradicts)": None, "confidence": e["confidence"],
                         "text": f"{other}: {_n['claim']}", "where": f"{_n['dataset']} {_n['kind']}/{_n['status']}", "explanation": e.get("explanation", ""), "quote": ""})
        else:
            rows.append({"relation": e["relation"], "P(supports)": e.get("p_replicated"), "P(contradicts)": e.get("p_contradicted"), "confidence": e["confidence"],
                         "text": "; ".join(f"{g}: log2fc {v['log2fc']}, padj {v['padj']:.2g}" for g, v in list(e["numbers"].items())[:4]),
                         "where": f"{other} {_n['material'][:30]} (comparable {e['comparable']})", "explanation": "", "quote": ""})
    nums = "; ".join(f"{g}: log2fc {v['log2fc']}, padj {v['padj']:.2g}, {v.get('carriers', '')}" for g, v in list(f["numbers"].items())[:4])
    mo.vstack([
        mo.md(f"### {f['id']} · {f['kind']} · critic: **{f['status']}**\n**{f['claim']}**  \n{nums}  \n_Why new (scout):_ {f['why_not_known']}  \n_Critic:_ {f['reason']}"),
        mo.md(f"{len(ego)} links at these thresholds; the {len(top)} strongest drawn."),
        mo.mermaid("\n".join(lines)) if top else mo.md("_No links at these thresholds._"),
        mo.ui.table(rows, selection=None, page_size=12) if rows else None,
    ])
    return


@app.cell
def _(mo, EX, f, ego, graph, N, json):
    # On-demand prose: a regular LLM explains this finding's accepted links and quotes the passage; saved back into the graph.
    can = EX.available()
    explain = mo.ui.run_button(label=f"Explain these {len(ego)} links with the LLM" if can else "Explain links (needs ANTHROPIC_API_KEY or WANDB_API_KEY in .env)",
                               kind="success", disabled=not can or not ego)
    explain
    return (explain,)


@app.cell
def _(mo, EX, C, explain, f, ego, graph, N, json):
    if explain.value:
        todo = [e for e in ego if e["type"] in ("finding-passage", "finding-finding") and not e.get("explanation")]
        fs = [n for n in graph["nodes"] if n["type"] == "finding"]
        ps = [{"id": n["id"], "text": n["text"]} for n in graph["nodes"] if n["type"] == "passage"]
        for _fn in fs:
            _fn.setdefault("table_facts", {g: v for g, v in _fn["numbers"].items()})
        with mo.status.spinner(title=f"Explaining {len(todo)} links"):
            EX.explain_edges(todo, fs, ps, progress=lambda s: None)
        json.dump(graph, open("results/graph.json", "w"))
        out = mo.vstack([mo.md(f"**{sum(1 for e in todo if e.get('explanation'))} links explained** (saved to results/graph.json; reload to see them in the table):")] +
                        [mo.md(f"- **{e['relation']}** → {e['explanation']}" + (f"  \n  > {e['quote']}" if e.get("quote") else "")) for e in todo if e.get("explanation")])
    else:
        out = None
    out
    return


if __name__ == "__main__":
    app.run()
