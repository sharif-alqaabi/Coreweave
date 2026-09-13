"""Helix demo deck: the whole presentation in one browser tab. Nine slides: the problem, the loop, the product, does it learn,
the proof, Helix on, TypeSafe verification across OSDR, the research graph, close; interactive lead and rulebook-version pickers. Everything is
preloaded from results/ and docs/ so nothing spins on stage.

    marimo run app/deck.py -p 2721

scripts/build_deck_site.py inlines the DATA block below into app/deck_site.py for the static export.
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", css_file="deck.css")


@app.cell
def _():
    import marimo as mo, json, difflib, os
    # DATA-START
    import glob
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
    os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv(".env")

    def _padj(l):
        ps = [f["padj"] for f in l.get("table_facts", {}).values() if isinstance(f, dict) and "padj" in f]
        return f"{min(ps):.2g}" if ps else ""

    def _slim(l, keep):
        return {k: l.get(k, "") for k in keep}

    def _flow_embed(html):
        # Style + figure only: the slide has its own heading, and .flow-root lets deck.css theme it.
        css = html.split("<style>", 1)[1].split("</style>", 1)[0]
        fig = "<figure" + html.split("<figure", 1)[1].split("</figure>", 1)[0] + "</figure>"
        return f'<div class="flow-root"><style>{css}</style>{fig}</div>'

    _naive = json.load(open("results/naive_OSD-255.json"))
    _prod = json.load(open("results/product_OSD-421.json"))
    _verdict = {k["id"]: k for k in _naive["killed"]}
    DATA = {
        "wb": f"https://wandb.ai/{os.getenv('WANDB_ENTITY', '')}/{os.getenv('WANDB_PROJECT', 'helix')}/weave",
        "naive": {"dataset": _naive["dataset"], "rules": os.path.basename(_naive["rules"]),
                  "code_check": _naive.get("code_check", {}), "v0_killed": _naive.get("v0", {}).get("killed", 0),
                  "leads": [{**_slim(l, ("id", "claim", "why_not_known", "next_step", "rows")),
                             "label": _verdict[l["id"]]["label"] if l["id"] in _verdict else "ok",
                             "reason": _verdict[l["id"]]["reason"] if l["id"] in _verdict else next((s["reason"] for s in _naive["survivors"] if s["id"] == l["id"]), ""),
                             "padj": _padj(next((x for x in _naive["survivors"] + _naive["killed"] if x["id"] == l["id"]), {}))}
                            for l in _naive["leads"]]},
        "prod": {"dataset": _prod["dataset"], "rules": os.path.basename(_prod["rules"]), "seconds": _prod["seconds"],
                 "leads": [{**_slim(j, ("id", "claim", "why_not_known", "next_step", "label", "reason")), "padj": _padj(j)}
                           for j in _prod["survivors"] + _prod["killed"]]},
        "flow_html": _flow_embed(open("docs/helix-flow-pitch.html").read()),
        "charts_html": "<style>" + open("docs/helix-charts.html").read().split("<style>", 1)[1],
        "rules": [],
    }
    _seen = set()
    for _v in sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3])):
        _t = open(_v).read()
        if _t in _seen:
            continue
        _seen.add(_t)
        _mp = _v.replace(".md", ".meta.json")
        DATA["rules"].append({"name": os.path.basename(_v), "text": _t, "meta": {"sections": json.load(open(_mp)).get("sections", [])} if os.path.exists(_mp) else {}})
    _ver = json.load(open("results/replicate_OSD-421.json"))
    _ex = next((l for l in _ver["leads"] if l["id"].endswith("lead_001")), _ver["leads"][0])
    DATA["verify"] = {
        "dataset": _ver["dataset"], "seconds": _ver["seconds"], "n_studies": _ver["n_studies"], "organism": _ver["organism"],
        "tables": sorted({n["osd_id"] for l in _ver["leads"] for n in l["numeric"] if n["comparable"] >= 2}),
        "leads": [{"id": l["id"], "claim": l["claim"], "shape": l["shape"], "verdict": l["verdict"], "scout": l["why_not_known"],
                   "genes": l.get("genes", [])[:3], "by": {n["osd_id"]: n["verdict"] for n in l["numeric"] if n["comparable"] >= 2}} for l in _ver["leads"]],
        "example": {"id": _ex["id"], "claim": _ex["claim"],
                    "where": [{"study": w["osd_id"], "tissue": w["material"][:32], "factor": w["factors"][:28], "assay": w["assay"][:22],
                               "comparable (0-3)": w["comparable"], "P(same factor)": w["same_factor"], "on disk": "yes" if w["on_disk"] else ""}
                              for w in _ex["where_to_look"][:8]],
                    "numbers": [{"study": n["osd_id"], "tissue": n["material"][:24], "verdict": n["verdict"], **n["agreement"],
                                 "numbers": "; ".join(f"{g}: log2fc {f['log2fc']}, padj {f['padj']:.2g}" for g, f in list(n["facts"].items())[:2]
                                                      if isinstance(f, dict) and isinstance(f.get("padj"), float) and f["padj"] == f["padj"])}
                                for n in _ex["numeric"] if n["comparable"] >= 2]},
    }
    _g = json.load(open("results/graph.json")); _N = {n["id"]: n for n in _g["nodes"]}
    _E = _g["edges"]
    _paper = lambda pid: (_N.get("pmid" + pid, {}).get("title", "")[:70] if pid else "OSDR study description")
    _contra = sorted([e for e in _E if e["type"] == "finding-passage" and e["relation"] == "contradicts"], key=lambda e: -e["p_contradicts"])
    _seen_f = set(); _contra_rows = []
    for e in _contra:                                                  # one passage per finding, strongest first
        if e["src"] in _seen_f or len(_contra_rows) >= 8:
            continue
        _seen_f.add(e["src"]); _pn = _N[e["dst"]]
        _contra_rows.append({"finding": e["src"], "claim": _N[e["src"]]["claim"][:80], "critic said": _N[e["src"]]["status"],
                             "P(contradicts)": e["p_contradicts"], "passage": _pn["text"][:260], "paper": _paper(_pn["pmid"])})
    _redis = [{"scout lead": e["src"], "claim": _N[e["src"]]["claim"][:70], "paper claim": e["dst"], "confidence": e["confidence"]}
              for e in _E if e["relation"] == "rediscovers" and _N[e["src"]]["kind"] != "paper_claim"]
    _e2 = next((n for n in _g["nodes"] if n["type"] == "finding" and n["id"] == "OSD-421_lead_003"), None)
    _sem = sorted([e for e in _E if _e2 and e["src"] == _e2["id"] and e["type"] == "finding-passage" and e["relation"] in ("supports", "consistent")],
                  key=lambda e: -e["p_supports"])[:3]
    _ego_src = "OSD-421_lead_001"
    _ego = sorted([e for e in _E if e["src"] == _ego_src and e["type"] in ("finding-passage", "finding-finding", "finding-dataset")
                   and e["relation"] not in ("from", "mentions", "background", "same_entity_different_claim", "inconclusive")],
                  key=lambda e: -(e.get("p_supports") or e.get("confidence") or 0))[:9]
    _judged = {k.split(":")[1]: v for k, v in _g["stats"]["edges"].items()
               if k.split(":")[0] in ("finding-passage", "finding-finding") or (k.startswith("finding-dataset:") and not k.endswith(":from"))}
    try:
        _n_pass = sum(1 for _ in open("data/corpus/passages.jsonl")); _n_pap = len(json.load(open("data/corpus/papers.json")))
    except Exception:
        _n_pass, _n_pap = 12152, 150
    DATA["graph"] = {
        "built": _g["built"], "seconds": _g["stats"]["seconds"], "nodes": _g["stats"]["nodes"], "judged": _judged,
        "pairs_scored": sum(_judged.values()) + _g["stats"]["judged_dropped"], "corpus_passages": _n_pass, "corpus_papers": _n_pap,
        "contradictions": _contra_rows, "rediscoveries": _redis,
        "semantic": {"claim": _e2["claim"] if _e2 else "", "hits": [{"relation": e["relation"], "P(supports)": e["p_supports"],
                                                                    "passage": _N[e["dst"]]["text"][:220], "paper": _paper(_N[e["dst"]]["pmid"])} for e in _sem]},
        "ego": {"claim": _N[_ego_src]["claim"][:70] if _ego_src in _N else "", "edges": [
            {"relation": e["relation"], "p": round(e.get("p_supports") if e["type"] == "finding-passage" else e.get("confidence", 0), 2),
             "type": _N[e["dst"]]["type"], "label": (_N[e["dst"]]["text"][:60] + "..." if _N[e["dst"]]["type"] == "passage" else _N[e["dst"]]["label"][:60])}
            for e in _ego if e["dst"] in _N]},
    }
    # DATA-END
    WB = DATA["wb"]
    VERSIONS = [  # scores from the Weave evaluations (holdout) and results/metrics.csv (train)
        {"name": "rules_v0", "author": "hand-written seed", "train": 0.68, "unseen": 0.58, "false_kills": 7, "missed": 20, "verdict": "baseline"},
        {"name": "rules_v1", "author": "Qwen", "train": 0.74, "unseen": 0.64, "false_kills": 8, "missed": 13, "verdict": "improved"},
        {"name": "rules_v2", "author": "ARIA", "train": 0.81, "unseen": 0.71, "false_kills": 10, "missed": 8, "verdict": "ships"},
        {"name": "rules_v3", "author": "nobody", "train": 0.81, "unseen": 0.71, "false_kills": 10, "missed": 8, "verdict": "copy of v2", "copy_of": "rules_v2"},
        {"name": "rules_v4", "author": "Qwen", "train": 0.84, "unseen": 0.64, "false_kills": 15, "missed": 8, "verdict": "caught: overfit"},
    ]
    REASON = {"ok": "survives", "contradicted": "contradicted by the table", "underpowered": "underpowered", "confound": "confounded by a few samples",
              "untestable": "untestable", "no_mechanism": "no mechanism", "already_known": "already known"}
    return mo, json, difflib, os, DATA, WB, VERSIONS, REASON


@app.cell
def _(mo):
    def cards(leads, judged, reason_names):
        """Finding cards; judged=True colours each by verdict and shows the critic's number."""
        import html as _html_2
        out = []
        for l in leads:
            ok = l["label"] == "ok"
            klass = "hx-card " + ("hx-ok" if ok else "hx-kill") if judged else "hx-card"
            tag = (f'<div class="hx-tag {"hx-tag-ok" if ok else "hx-tag-kill"}">{"survives" if ok else reason_names.get(l["label"], l["label"])}</div>'
                   f'<div class="hx-num">{_html_2.escape(l["reason"][:150])}</div>') if judged else ""
            out.append(f'<div class="{klass}"><div class="hx-claim">{_html_2.escape(l["claim"])}</div>'
                       f'<div class="hx-why">{_html_2.escape(l["why_not_known"][:140])}</div>{tag}</div>')
        return mo.Html('<div class="hx-cards" tabindex="0" role="region" aria-label="Research findings">' + "".join(out) + "</div>")

    def stat(value, label, caption="", kind=""):
        return mo.Html(f'<div class="hx-stat {kind}"><div class="hx-v">{value}</div><div class="hx-l">{label}</div><div class="hx-c">{caption}</div></div>')

    def stats(*items):
        return mo.Html('<div class="hx-stats">' + "".join(s.text for s in items) + "</div>")
    return cards, stat, stats


@app.cell
def _(mo, DATA, REASON, cards, stat, stats):
    _leads = DATA["naive"]["leads"]
    _killed = [l for l in _leads if l["label"] != "ok"]
    _paper = {"Drd4": "the paper's most significant gene", "H2bc4": "Hist1h2bc, the paper's aging link", "Sag": "the paper's top retinitis-pigmentosa gene"}
    _found = [(g, why) for g, why in _paper.items() if any(g in l["rows"] for l in _leads if l["label"] == "ok")]
    _on = False
    _cc = DATA["naive"]["code_check"]
    _flagged = set(_cc.get("unsupported", [])) | set(_cc.get("uncharacterised", []))
    _tiles = stats(stat(len(_leads), "findings reported", "from one NASA retina table"),
                   stat(0, "checked by the assistant", "it wrote the numbers too"),
                   stat(len(_flagged), "have a visible problem", f"{len(_cc.get('unsupported', []))} the table contradicts · {len(_cc.get('uncharacterised', []))} rest on genes nobody has characterised", "hx-bad"))
    _method = mo.md(f"_The third tile is a plain code check against the table: padj above 0.05 or the wrong direction, or a Gm/Rik gene symbol. No rules, no model, no Helix. "
                    f"It is the floor, what anyone with the CSV and ten minutes could find. Another {len(_cc.get('nothing', []))} cite no gene at all, so the check cannot reach them._")
    _intro = (mo.md("**Same sixty findings.** Code attached each one's real numbers from the table, and a separate critic judged every one. "
                    "Green survives. Red is killed, with the number.")
              if _on else
              mo.md("Dataset OSD-255, mice flown 35 days on the ISS. An LLM read the table and reported sixty findings. "
                    "Confident, specific, a suggested experiment for each. **None of it checked**, because nothing in the loop can say no."))
    _redisc = (mo.callout(mo.md("**And the survivors include what the scientists actually published.** The scout never saw the paper. "
                                "From the table alone it proposed, and the critic passed: " + "; ".join(f"**{g}**, {w}" for g, w in _found) + "."), kind="success")
               if _on and _found else mo.md(""))
    _tells = [("The Slc family shows coordinated downregulation", "One of the four genes it lists, Slc25a19, goes the other way in the table (+0.39). The model asserted a direction that is false."),
              ("n-R5s118 and n-R5s106 show borderline upregulation", "Its own number says padj 0.099. That is not significant. Dressed up as ribosomal stress anyway."),
              ("Gm26244 has high fold change (+1.57) but padj=0.24", "padj 0.24 is noise. The model argues past its own statistic and calls it a possible false negative."),
              ("Gm16638 is upregulated in spaceflight", "Why it matters: 'no known function, so its response is novel'. Novel because nobody knows what it does. Nothing to test.")]
    import html as _html_3
    _look = []
    for _pre, _tell in _tells:
        _l = next((l for l in _leads if l["claim"].startswith(_pre)), None)
        if _l:
            _look.append(f'<div class="hx-card hx-kill"><div class="hx-claim">{_html_3.escape(_l["claim"])}</div>'
                         f'<div class="hx-why">{_html_3.escape(_l["why_not_known"][:140])}</div><div class="hx-tell">{_html_3.escape(_tell)}</div></div>')
    _closer = mo.vstack([mo.md("## Look closer. We checked four by hand."),
                         mo.Html('<div class="hx-cards hx-short">' + "".join(_look) + "</div>"),
                         mo.callout(mo.md("**Believable is the problem.** Every one of the sixty reads like the four above did before we checked. "
                                          "A scientist cannot tell which are like this without looking up every number: about a week per table. "
                                          "Nothing in this assistant is allowed to say no."), kind="danger")])
    slide1 = mo.vstack([mo.md("# An LLM research assistant reads a NASA retina study"), _intro, _tiles, _method, cards(_leads, False, REASON), _closer])
    return (slide1,)


@app.cell
def _(mo, DATA, REASON, cards, stat, stats):
    _leads = DATA["naive"]["leads"]
    _killed = [l for l in _leads if l["label"] != "ok"]
    _paper = {"Drd4": "the paper's most significant gene", "H2bc4": "Hist1h2bc, the paper's aging link", "Sag": "the paper's top retinitis-pigmentosa gene"}
    _found = [(g, why) for g, why in _paper.items() if any(g in l["rows"] for l in _leads if l["label"] == "ok")]
    _on = True
    _v0 = DATA["naive"]["v0_killed"]
    _tiles = mo.vstack([
        stats(stat(0, "killed with no critic", "slide 1: the assistant alone"),
              stat(_v0, "killed by the hand-written rules", "rules_v0, before any learning"),
              stat(len(_killed), "killed by ARIA’s rules", "rules_v2, chosen on unseen data", "hx-bad")),
        stats(stat(len(_leads) - len(_killed), "findings survive", "each backed by the table's numbers", "hx-good"),
              stat(len(_found), "published headline genes", "rediscovered from the table alone", "hx-good"),
              stat("4 of 4", "hand-checked tells killed", "the ones from slide 1"))])
    _cc = DATA["naive"]["code_check"]; _strict = set(_cc.get("unsupported", [])) | set(_cc.get("uncharacterised", []))
    _kids = {l["id"] for l in _killed}
    _agree, _spared, _extra = len(_strict & _kids), len(_strict - _kids), len(_kids - _strict)
    _recon = mo.callout(mo.md(f"**Against the crude check from slide 1.** It flagged {len(_strict)}. The critic killed {_agree} of them and passed {_spared} the check misread: "
                              f"claims that correctly describe a gene as unchanged. It also killed {_extra} the check cannot see: a false claim about the whole table, "
                              "a confound, an untestable claim, and a real gene with no mechanism. Same floor, better judgment, and a reason on every one."), kind="neutral")
    _intro = (mo.md("**Same sixty findings.** Code attached each one's real numbers from the table, and a separate critic judged every one with ARIA’s rules_v2.md. Green survives. Red is killed, with the number.")
              if _on else mo.md("The sixty findings from slide 1, exactly as the assistant wrote them. Nothing has been checked yet."))
    _redisc = (mo.callout(mo.md("**And the survivors include what the scientists actually published.** The scout never saw the paper. From the table alone it proposed, and the critic passed: "
                                + "; ".join(f"**{g}**, {w}" for g, w in _found) + "."), kind="success") if _on and _found else mo.md(""))
    slide6 = mo.vstack([mo.md("# The same sixty, through Helix"), _intro, _tiles, _recon, cards(_leads, _on, REASON), _redisc])
    return (slide6,)


@app.cell
def _(mo, DATA):
    slide2 = mo.vstack([mo.md("# How it works"),
                        mo.md("**Propose, judge, rewrite the rules, repeat.** We didn't teach the model what a good lead is. We let it propose, and let the numbers sort."),
                        mo.Html(DATA["flow_html"])])
    return (slide2,)


@app.cell
def _(mo, DATA):
    _leads = DATA["prod"]["leads"]
    pick = mo.ui.dropdown(options={f'{"✓" if l["label"] == "ok" else "✗"}  {l["claim"][:90]}': l["id"] for l in _leads},
                          value=f'{"✓" if _leads[0]["label"] == "ok" else "✗"}  {_leads[0]["claim"][:90]}', label="Pick a lead")
    return (pick,)


@app.cell
def _(mo, DATA, REASON, stat, stats, pick):
    _p = DATA["prod"]; _leads = _p["leads"]
    _surv = [l for l in _leads if l["label"] == "ok"]; _kill = [l for l in _leads if l["label"] != "ok"]
    _l = next(l for l in _leads if l["id"] == pick.value)
    _ok = _l["label"] == "ok"
    _detail = mo.Html(f'''<div class="hx-detail {"hx-ok" if _ok else "hx-kill"}">
      <div class="hx-tag {"hx-tag-ok" if _ok else "hx-tag-kill"}">{"survives" if _ok else REASON.get(_l["label"], _l["label"])}</div>
      <div class="hx-claim hx-big">{_l["claim"]}</div>
      <div class="hx-row"><span class="hx-k">why new</span><span>{_l["why_not_known"]}</span></div>
      <div class="hx-row"><span class="hx-k">next step</span><span>{_l["next_step"]}</span></div>
      <div class="hx-row"><span class="hx-k">padj</span><span>{_l["padj"] or "no single gene"}</span></div>
      <div class="hx-row"><span class="hx-k">critic</span><span class="hx-num">{_l["reason"]}</span></div></div>''')
    slide3 = mo.vstack([
        mo.md("# The product: any table in, judged leads out"),
        mo.md(f"A different study, **{_p['dataset']}** (thymus). One upload, {_p['seconds']} seconds, rules **{_p['rules']}**. Live at [localhost:2719](http://localhost:2719)."),
        stats(stat(len(_surv), "leads survive", "hypotheses worth a scientist's time", "hx-good"), stat(len(_kill), "leads killed", "with the number that decided it", "hx-bad"),
              stat(f"{_p['seconds']} s", "per table", "summarise, propose, attach numbers, judge")),
        mo.hstack([pick], justify="start"), _detail])
    return (slide3,)


@app.cell
def _(mo, VERSIONS):
    version_pick = mo.ui.radio(options=[v["name"] for v in VERSIONS], value="rules_v2", label="Rulebook version", inline=True)
    return (version_pick,)


@app.cell
def _(mo, DATA, VERSIONS, difflib, stat, stats, version_pick):
    _i = [v["name"] for v in VERSIONS].index(version_pick.value)
    _v = VERSIONS[_i]
    _kind = "hx-good" if _v["verdict"] == "ships" else ("hx-bad" if "caught" in _v["verdict"] else "")
    _tiles = stats(stat(f"{_v['train']:.2f}", "score on training leads", "what the loop optimises"),
                   stat(f"{_v['unseen']:.2f}", "score on unseen leads", "what decides what ships", _kind),
                   stat(_v["false_kills"], "good leads killed", "of 90 unseen", "hx-bad" if _v["false_kills"] >= 15 else ""),
                   stat(_v["missed"], "bad leads passed", "of 90 unseen"),
                   stat(_v["author"], "rulebook source", _v["verdict"], _kind))
    _rules = DATA["rules"]; _cur = next(r for r in _rules if r["name"] == _v.get("copy_of", _v["name"]) + ".md")

    def _github_diff(lines):
        import html as _html_9
        style = {"+": "hx-diff-add", "-": "hx-diff-remove", "@": "hx-diff-hunk", " ": ""}
        rows = []
        for ln in lines:
            if ln.startswith(("+++", "---")): continue
            k = ln[:1] if ln[:1] in style else " "
            rows.append(f'<div class="hx-diff-row {style[k]}"><span class="hx-diff-sign">{_html_9.escape(k.strip())}</span>'
                        f'<span class="hx-diff-text">{_html_9.escape(ln[1:] if k != " " else ln)}</span></div>')
        return '<div class="hx-diff">' + "".join(rows) + "</div>"
    if _v.get("copy_of"):
        _change = mo.callout(mo.md(f"**{_v['name']} is byte-for-byte identical to {_v['copy_of']}.** In round 2, three architects proposed patches and none scored higher "
                                   "than v2 on the training leads, so the loop copied v2 forward unchanged. The same happened for v5 to v8 after v4: three more rounds, no winner. "
                                   "Copies are not shown on the charts because they are not different rulebooks."), kind="neutral")
    elif _i == 0:
        _change = mo.vstack([mo.md("**The seed.** Seven reasons to say no, each with a numeric threshold, written by hand before any training."),
                             mo.accordion({"read rules_v0": mo.md(_cur["text"])})])
    else:
        _prev = next(r for r in _rules if r["name"] == VERSIONS[_i - 1].get("copy_of", VERSIONS[_i - 1]["name"]) + ".md")
        _d = difflib.unified_diff(_prev["text"].splitlines(), _cur["text"].splitlines(), fromfile=_prev["name"], tofile=_cur["name"], lineterm="", n=1)
        _sections = ", ".join(_cur["meta"].get("sections", []))
        _note = {"rules_v1": "Qwen tightened the numeric thresholds.", "rules_v2": "ARIA added principles and generic examples. This is the version that holds up on unseen data.",
                 "rules_v4": "Qwen replaced the untestable rule with one that names five training leads by id. Memorising, not learning. Best on train, worse on everything else."}[_v["name"]]
        _change = mo.vstack([mo.md(f"**Changes in {_v['name']}** ({_sections}). {_note}"), mo.Html(_github_diff(_d))])
    _verdict_line = (mo.callout(mo.md("**This page caught it.** v4 scored best on training data and killed five more good leads on unseen data for no extra junk caught. It did not ship."), kind="danger")
                     if _v["name"] == "rules_v4" else
                     mo.callout(mo.md("**ARIA’s rules_v2.md ships.** It scored best on unseen leads, turning ARIA’s rule improvements into the rulebook used by Helix."), kind="success")
                     if _v["name"] == "rules_v2" else mo.md(""))
    slide4 = mo.vstack([mo.md("# Does it learn? Every rewrite, scored on leads it never saw"),
                        mo.hstack([version_pick], justify="start"),
                        mo.md("_Eight versions were written; four are distinct. v3 is a copy of v2 and v5 to v8 are copies of v4: rounds where no candidate beat the current rulebook._"),
                        _tiles, _verdict_line, _change,
                        mo.md("## The four distinct rulebooks at once"), mo.Html(DATA["charts_html"])])
    return (slide4,)


@app.cell
def _(mo, WB, stat, stats):
    _nasa = [{"set": "LLM holdout, 90 unseen leads", "v0": "27 mistakes", "v1": "21", "v2 (ships)": "18", "v4 (caught)": "23"},
             {"set": "OSD-255 retina paper, 34 claims", "v0": "0 false kills", "v1": "0", "v2 (ships)": "0", "v4 (caught)": "0"},
             {"set": "OSD-467 bone paper, 20 claims, never trained on", "v0": "0 false kills", "v1": "0", "v2 (ships)": "0", "v4 (caught)": "0"}]
    slide5 = mo.vstack([
        mo.md("# The proof is public"),
        stats(stat("5,845", "critic verdicts", "each a Weave trace with what the critic saw"), stat("4", "rulebooks", "each a versioned W&B artifact"),
              stat("12", "evaluations", "every version on every lead set"), stat("0", "published findings killed", "54 claims from two NASA papers", "hx-good")),
        mo.hstack([mo.Html(f'<a class="hx-btn" href="{WB}/evaluations" target="_blank">Open the Evals</a>'),
                   mo.Html(f'<a class="hx-btn hx-dark" href="{WB}/traces" target="_blank">Open the Traces</a>')], justify="start"),
        mo.ui.table(_nasa, selection=None),
        mo.callout(mo.md("**Zero published NASA findings killed, by any version.** Every unsupported claim killed with the number that decided it."), kind="success")])
    return (slide5,)


@app.cell
def _(mo):
    slide9 = mo.Html('<div class="hx-close"><h1>Agents drift.</h1><h2>Usually a person notices, after trusting it.</h2>'
                     '<h2>Here the loop noticed first, on data nobody tuned for, and the bad version never reached a user.</h2>'
                     '<p>Helix · built 12–13 Sep 2026 · Weave · W&amp;B Inference · W&amp;B Automations + ARIA · marimo · TypeSafe</p></div>')
    return (slide9,)


@app.cell
def _(mo, DATA, stat, stats):
    _v = DATA["verify"]; _leads = _v["leads"]
    _rep = [l for l in _leads if l["verdict"].startswith("replicated in ")]
    _not = [l for l in _leads if l["verdict"].startswith("not replicated")]
    _unique = ", ".join(", ".join(l["genes"]) or l["claim"][:30] for l in _not)
    _where_rep = sorted({d.strip() for l in _rep for d in l["verdict"].split(" in ", 1)[1].split(",")})
    _matrix = [{"lead": l["id"].split("_", 1)[1], "claim": l["claim"][:70], "OSDR check": l["verdict"][:40],
                **{k: l["by"][k][:14] for k in _v["tables"] if k in l["by"]}, "scout said": l["scout"][:70]} for l in _leads]
    slide7 = mo.vstack([
        mo.md("# Then TypeSafe checks every survivor against the rest of OSDR"),
        mo.md(f"Every survivor on slide 3 says *why it is new*, usually \"not replicated in other spaceflight studies\". Nobody checks. "
              f"**TypeSafe (Jev)** does: for each of the {len(_leads)} survivors it scores how well every one of the {_v['n_studies']} "
              f"{_v['organism']} studies in the OSDR catalog could replicate or refute it, then pandas looks the genes up in the comparable "
              f"tables and Jev judges what the numbers mean given the tissue. Direction and significance are arithmetic; the verdict is a code rule."),
        stats(stat(len(_leads), "survivors checked", f"against {_v['n_studies']} catalog studies"),
              stat(len(_rep), "replicate elsewhere", "in another spaceflight-thymus flight", "hx-good"),
              stat(len(_not), "seen nowhere else", _unique or "", "hx-bad"),
              stat(f"{_v['seconds']} s", "for the whole check", "probabilities stored, thresholds are sliders")),
        mo.callout(mo.md(f"**The scout's novelty claim was wrong on {len(_rep)} of {len(_leads)}.** The biology is robust, it just isn't new: "
                         f"the same genes move the same way in {', '.join(_where_rep)}, independent spaceflight-thymus RNA-seq flights. "
                         f"What *is* unique to this study: **{_unique}**. That is the lead a scientist should spend time on."), kind="success"),
        mo.md(f"**Tier 1, where to look.** Jev's comparability for the top catalog studies for *{_v['example']['claim'][:60]}*: "
              "the thymus flights score 3 (direct test), muscle and kidney about 1, with no downloads."),
        mo.ui.table(_v["example"]["where"], selection=None, page_size=8),
        mo.md("**Tier 2, the numbers.** For the tables on disk, the per-gene tally is pandas; Jev's verdict is gated by it."),
        mo.ui.table(_v["example"]["numbers"], selection=None, page_size=6),
        mo.md("**Every survivor, every comparable dataset.** replicated · not_replicated · underpowered · not_detected."),
        mo.ui.table(_matrix, selection=None, page_size=8),
        mo.md("_Live in **Lead Lab** ([localhost:2719](http://localhost:2719)): the **OSDR check** column on the survivors table and the "
              "**Verify with TypeSafe** button rerun this in 15 s. The critic's verdict is never changed by it._"),
    ])
    return (slide7,)


@app.cell
def _(mo, DATA, stat, stats):
    _g = DATA["graph"]; _n = _g["nodes"]; _j = _g["judged"]
    _lines = ["graph LR", f'  F["{_g["ego"]["claim"].replace(chr(34), "")}"]:::finding']
    _style = {"passage": "fill:#e6f0ff,stroke:#3060c0", "finding": "fill:#ffe8b0,stroke:#b07a00", "dataset": "fill:#e0f5e0,stroke:#2a7a2a"}
    for _i, _e in enumerate(_g["ego"]["edges"]):
        _arrow = "==>" if _e["relation"] in ("replicated", "contradicts", "contradicted", "supports", "rediscovers") else "-->"
        _lines.append(f'  N{_i}["{_e["label"].replace(chr(34), "")}"]:::{_e["type"]}')
        _lines.append(f'  F {_arrow}|{_e["relation"]} {_e["p"]:.2f}| N{_i}')
    _lines += [f"  classDef {k} {v}" for k, v in _style.items()]
    _sem = _g["semantic"]
    slide8 = mo.vstack([
        mo.md("# The research graph: every finding, linked to the papers that support or contradict it"),
        mo.md(f"**{_n['finding']} findings** (scout leads, product survivors, the 54 NASA paper claims) against **{_g['corpus_papers']} papers** from the OSDR "
              f"catalog, {_g['corpus_passages']:,} passages of abstract and open-access full text, plus {_n['dataset']} datasets and {_n['gene']} genes. "
              f"Code proposes candidate pairs from shared entities; **TypeSafe** reranks a broad passage pool for relevance, then types each pair "
              f"(supports · contradicts · background · rediscovers · replicates · extends), {_g['pairs_scored']:,} pairs in {_g['seconds']} s. "
              "Every edge keeps its probabilities; a regular LLM only writes the one-sentence explanation of links already accepted."),
        stats(stat(_n["finding"], "findings", "nodes"), stat(_n.get("passage", 0), "passages linked", f"from {_n.get('paper', 0)} papers"),
              stat(_j.get("supports", 0) + _j.get("consistent", 0), "supported by a passage", "direct or at the pathway level", "hx-good"),
              stat(_j.get("contradicts", 0), "contradicted by a passage", "opposite direction or explicitly no change", "hx-bad"),
              stat(len(_g["rediscoveries"]), "rediscoveries", "scout lead matches a published claim", "hx-good"),
              stat(_j.get("replicated", 0), "replicated by numbers", "in another dataset's table")),
        mo.md("## Contradicted by the literature"),
        mo.md("_The strongest per finding. Jev's dedicated P(contradicts) gates the label, so a passage that merely lists the gene cannot count._"),
        mo.ui.table(_g["contradictions"], selection=None, page_size=5),
        mo.callout(mo.md("**Crb1 \"downregulated in the spaceflight retina\"** was contradicted by the retina paper's own sentence: "
                         "*\"None of the disease-associated genes that were shared across multiple diseases were differentially expressed in spaceflight.\"* "
                         "That is the sentence our human labeller cited, found by TypeSafe in twelve thousand passages."), kind="danger"),
        mo.md("## Rediscoveries: the scout's leads matched to what the scientists published"),
        mo.ui.table(_g["rediscoveries"], selection=None, page_size=5),
        mo.md(f"## Semantic, not keyword: *{_sem['claim'][:70]}*"),
        mo.md("_E2f7 is named in no paper. The rerank still reached the OSD-515 thymus paper's cell-cycle result, and Jev called it support at the pathway level._"),
        mo.ui.table(_sem["hits"], selection=None, page_size=3),
        mo.md(f"## One finding's neighbourhood: *{_g['ego']['claim']}*"),
        mo.mermaid("\n".join(_lines)),
        mo.md("_Live in **Graph Lab** ([localhost:2722](http://localhost:2722)): pick any finding or gene, move the thresholds, read the passages, "
              "and ask the LLM to explain a link._"),
    ])
    return (slide8,)


@app.cell
def _(mo, slide1, slide2, slide3, slide4, slide5, slide6, slide7, slide8, slide9):
    _keys = mo.Html('<iframe style="display:none" srcdoc="<script>'
                    'parent.document.addEventListener(&quot;keydown&quot;, function(e){'
                    'if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;'
                    'if (e.composedPath().some(function(el){return el.matches && el.matches(&quot;input,textarea,select,button,[role=tablist],[role=combobox],[role=radio],[contenteditable=true]&quot;);})) return;'
                    'var d = (e.key===&quot;ArrowRight&quot;||e.key===&quot;PageDown&quot;) ? 1 : (e.key===&quot;ArrowLeft&quot;||e.key===&quot;PageUp&quot;) ? -1 : 0;'
                    'if (!d) return; var host = parent.document.querySelector(&quot;marimo-tabs&quot;);'
                    'var root = (host && host.shadowRoot) || parent.document;'
                    'var tabs = Array.from(root.querySelectorAll(&quot;[role=tab]&quot;)); if (!tabs.length) return;'
                    'var i = tabs.findIndex(function(t){return t.getAttribute(&quot;aria-selected&quot;)===&quot;true&quot; || t.dataset.state===&quot;active&quot;;});'
                    'var n = Math.min(Math.max(i + d, 0), tabs.length - 1); if (n !== i) { tabs[n].click(); e.preventDefault(); window.parent.scrollTo(0,0); }'
                    '});</script>"></iframe>')
    mo.vstack([_keys, mo.ui.tabs({"1 · The problem": slide1, "2 · How it works": slide2, "3 · The product": slide3, "4 · Does it learn?": slide4,
                                  "5 · The proof": slide5, "6 · Helix on": slide6, "7 · Verify across OSDR": slide7, "8 · Research graph": slide8,
                                  "9 · Close": slide9})])
    return


if __name__ == "__main__":
    app.run()
