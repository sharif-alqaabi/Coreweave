"""Helix demo deck: the whole presentation in one browser tab. Six slides as tabs, three of them
interactive (a with/without Helix switch, a lead picker, a rulebook-version picker). Everything is
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

    _naive = json.load(open("results/naive_OSD-255.json"))
    _prod = json.load(open("results/product_OSD-421.json"))
    _verdict = {k["id"]: k for k in _naive["killed"]}
    DATA = {
        "wb": f"https://wandb.ai/{os.getenv('WANDB_ENTITY', '')}/{os.getenv('WANDB_PROJECT', 'helix')}/weave",
        "naive": {"dataset": _naive["dataset"], "rules": os.path.basename(_naive["rules"]),
                  "leads": [{**_slim(l, ("id", "claim", "why_not_known", "next_step", "rows")),
                             "label": _verdict[l["id"]]["label"] if l["id"] in _verdict else "ok",
                             "reason": _verdict[l["id"]]["reason"] if l["id"] in _verdict else next((s["reason"] for s in _naive["survivors"] if s["id"] == l["id"]), ""),
                             "padj": _padj(next((x for x in _naive["survivors"] + _naive["killed"] if x["id"] == l["id"]), {}))}
                            for l in _naive["leads"]]},
        "prod": {"dataset": _prod["dataset"], "rules": os.path.basename(_prod["rules"]), "seconds": _prod["seconds"],
                 "leads": [{**_slim(j, ("id", "claim", "why_not_known", "next_step", "label", "reason")), "padj": _padj(j)}
                           for j in _prod["survivors"] + _prod["killed"]]},
        "flow_html": "<style>" + open("docs/helix-flow.html").read().split("<style>", 1)[1],
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
        DATA["rules"].append({"name": os.path.basename(_v), "text": _t, "meta": json.load(open(_mp)) if os.path.exists(_mp) else {}})
    # DATA-END
    WB = DATA["wb"]
    VERSIONS = [  # scores from the Weave evaluations (holdout) and results/metrics.csv (train)
        {"name": "rules_v0", "author": "hand-written seed", "train": 0.68, "unseen": 0.58, "false_kills": 7, "missed": 20, "verdict": "baseline"},
        {"name": "rules_v1", "author": "Qwen", "train": 0.74, "unseen": 0.64, "false_kills": 8, "missed": 13, "verdict": "improved"},
        {"name": "rules_v2", "author": "DeepSeek", "train": 0.81, "unseen": 0.71, "false_kills": 10, "missed": 8, "verdict": "ships"},
        {"name": "rules_v4", "author": "ARIA", "train": 0.84, "unseen": 0.64, "false_kills": 15, "missed": 8, "verdict": "caught: overfit"},
    ]
    REASON = {"ok": "survives", "contradicted": "contradicted by the table", "underpowered": "underpowered", "confound": "confounded by a few samples",
              "untestable": "untestable", "no_mechanism": "no mechanism", "already_known": "already known"}
    return mo, json, difflib, os, DATA, WB, VERSIONS, REASON


@app.cell
def _(mo):
    def cards(leads, judged, reason_names):
        """Finding cards; judged=True colours each by verdict and shows the critic's number."""
        import html as _h
        out = []
        for l in leads:
            ok = l["label"] == "ok"
            klass = "hx-card " + ("hx-ok" if ok else "hx-kill") if judged else "hx-card"
            tag = (f'<div class="hx-tag {"hx-tag-ok" if ok else "hx-tag-kill"}">{"survives" if ok else reason_names.get(l["label"], l["label"])}</div>'
                   f'<div class="hx-num">{_h.escape(l["reason"][:150])}</div>') if judged else ""
            out.append(f'<div class="{klass}"><div class="hx-claim">{_h.escape(l["claim"])}</div>'
                       f'<div class="hx-why">{_h.escape(l["why_not_known"][:140])}</div>{tag}</div>')
        return mo.Html('<div class="hx-cards">' + "".join(out) + "</div>")

    def stat(value, label, caption="", kind=""):
        return mo.Html(f'<div class="hx-stat {kind}"><div class="hx-v">{value}</div><div class="hx-l">{label}</div><div class="hx-c">{caption}</div></div>')

    def stats(*items):
        return mo.Html('<div class="hx-stats">' + "".join(s.text for s in items) + "</div>")
    return cards, stat, stats


@app.cell
def _(mo):
    helix_on = mo.ui.switch(label="**Helix on**", value=False)
    return (helix_on,)


@app.cell
def _(mo, DATA, REASON, cards, stat, stats, helix_on):
    _leads = DATA["naive"]["leads"]
    _killed = [l for l in _leads if l["label"] != "ok"]
    _paper = {"Drd4": "the paper's most significant gene", "H2bc4": "Hist1h2bc, the paper's aging link", "Sag": "the paper's top retinitis-pigmentosa gene"}
    _found = [(g, why) for g, why in _paper.items() if any(g in l["rows"] for l in _leads if l["label"] == "ok")]
    _on = helix_on.value
    _tiles = (stats(stat(len(_leads) - len(_killed), "findings survive", "each backed by the table's numbers", "hx-good"),
                    stat(len(_killed), "findings killed", "each with the number that decided it", "hx-bad"),
                    stat(len(_found), "published headline genes", "rediscovered from the table alone", "hx-good"))
              if _on else
              stats(stat(len(_leads), "findings reported", "from one NASA retina table"),
                    stat(0, "checked against the data", "the model wrote the numbers too"),
                    stat("?", "worth a scientist's time", "no way to tell")))
    _intro = (mo.md("**Same sixty findings.** Code attached each one's real numbers from the table, and a separate critic judged every one. "
                    "Green survives. Red is killed, with the number.")
              if _on else
              mo.md("Dataset OSD-255, mice flown 35 days on the ISS. An LLM read the table and reported sixty findings. "
                    "Confident, specific, a suggested experiment for each. **None of it checked**, because nothing in the loop can say no."))
    _redisc = (mo.callout(mo.md("**And the survivors include what the scientists actually published.** The scout never saw the paper. "
                                "From the table alone it proposed, and the critic passed: " + "; ".join(f"**{g}**, {w}" for g, w in _found) + "."), kind="success")
               if _on and _found else mo.md(""))
    slide1 = mo.vstack([mo.md("# An LLM research assistant reads a NASA retina study"),
                        mo.hstack([helix_on], justify="start"), _intro, _tiles, cards(_leads, _on, REASON), _redisc])
    return (slide1,)


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
                   stat(_v["author"], "written by", _v["verdict"], _kind))
    _rules = DATA["rules"]; _cur = next(r for r in _rules if r["name"] == _v["name"] + ".md")

    def _github_diff(lines):
        import html as _h
        style = {"+": "background:#e6ffec;color:#1a7f37", "-": "background:#ffebe9;color:#cf222e", "@": "background:#ddf4ff;color:#0550ae", " ": "color:#57606a"}
        rows = []
        for ln in lines:
            if ln.startswith(("+++", "---")): continue
            k = ln[:1] if ln[:1] in style else " "
            rows.append(f'<div style="{style[k]};display:flex;font:13px/1.5 ui-monospace,Menlo,monospace"><span style="width:1.4em;flex:none;text-align:center">{_h.escape(k.strip())}</span>'
                        f'<span style="white-space:pre-wrap;word-break:break-word">{_h.escape(ln[1:] if k != " " else ln)}</span></div>')
        return '<div style="border:1px solid #d0d7de;border-radius:6px;overflow:hidden;background:#fff;color:#1f2328">' + "".join(rows) + "</div>"
    if _i == 0:
        _change = mo.vstack([mo.md("**The seed.** Seven reasons to say no, each with a numeric threshold, written by hand before any training."),
                             mo.accordion({"read rules_v0": mo.md(_cur["text"])})])
    else:
        _prev = next(r for r in _rules if r["name"] == VERSIONS[_i - 1]["name"] + ".md")
        _d = difflib.unified_diff(_prev["text"].splitlines(), _cur["text"].splitlines(), fromfile=_prev["name"], tofile=_cur["name"], lineterm="", n=1)
        _sections = ", ".join(_cur["meta"].get("sections", []))
        _note = {"rules_v1": "Qwen tightened the numeric thresholds.", "rules_v2": "DeepSeek added principles and generic examples. This is the version that holds up on unseen data.",
                 "rules_v4": "ARIA replaced the untestable rule with one that names five training leads by id. Memorising, not learning. Best on train, worse on everything else."}[_v["name"]]
        _change = mo.vstack([mo.md(f"**What {_v['author']} changed** ({_sections}). {_note}"), mo.Html(_github_diff(_d))])
    _verdict_line = (mo.callout(mo.md("**This page caught it.** v4 scored best on training data and killed seven more good leads on unseen data for no extra junk caught. It did not ship."), kind="danger")
                     if _v["name"] == "rules_v4" else
                     mo.callout(mo.md("**This is what ships.** Not the newest rulebook, the one that measured best on leads it never saw."), kind="success")
                     if _v["name"] == "rules_v2" else mo.md(""))
    slide4 = mo.vstack([mo.md("# Does it learn? Every rewrite, scored on leads it never saw"),
                        mo.hstack([version_pick], justify="start"), _tiles, _verdict_line, _change,
                        mo.md("## All four at once"), mo.Html(DATA["charts_html"])])
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
    slide6 = mo.Html('<div class="hx-close"><h1>Agents drift.</h1><h2>Usually a person notices, after trusting it.</h2>'
                     '<h2>Here the loop noticed first, on data nobody tuned for, and the bad version never reached a user.</h2>'
                     '<p>Helix · built 12–13 Sep 2026 · Weave · W&amp;B Inference · W&amp;B Automations + ARIA · marimo</p></div>')
    return (slide6,)


@app.cell
def _(mo, slide1, slide2, slide3, slide4, slide5, slide6):
    mo.ui.tabs({"1 · The problem": slide1, "2 · How it works": slide2, "3 · The product": slide3,
                "4 · Does it learn?": slide4, "5 · The proof": slide5, "6 · Close": slide6})
    return


if __name__ == "__main__":
    app.run()
