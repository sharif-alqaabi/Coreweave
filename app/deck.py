"""Helix demo deck: the whole presentation in one browser tab. Each tab is a slide; everything is
preloaded from results/ and docs/ so nothing spins on stage. The two W&B pages open as buttons
(W&B does not allow itself to be embedded).

    marimo run app/deck.py -p 2721

Slide 1 needs results/naive_OSD-255.json (scout-only findings + the critic's verdicts on them):
    python3 -c "from helix.product import run_naive, judge_leads; ..."   # see scripts in DEMO.md
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo, os, sys, json, glob, difflib
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
    sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
    from dotenv import load_dotenv; load_dotenv(".env")
    WB = f"https://wandb.ai/{os.getenv('WANDB_ENTITY', '')}/{os.getenv('WANDB_PROJECT', 'helix')}/weave"
    def load(path):
        return json.load(open(path)) if os.path.exists(path) else None
    def html_file(path):
        t = open(path).read(); return t[t.index("<style>"):]
    return mo, os, json, glob, difflib, WB, load, html_file


@app.cell
def _(mo, load):
    naive = load("results/naive_OSD-255.json")
    reveal = mo.ui.run_button(label="Reveal: what Helix's critic says about these", kind="success", disabled=naive is None)
    return naive, reveal


@app.cell
def _(mo, naive, reveal):
    _PAPER = {"Drd4": "the paper's single most significant gene (circadian rhythm)", "H2bc4": "Hist1h2bc, the paper's aging link",
             "Sag": "the paper's top retinitis-pigmentosa gene"}
    if naive is None:
        slide1 = mo.md("_results/naive_OSD-255.json missing. Build it first (see DEMO.md)._")
    else:
        _rows = [{"finding": l["claim"], "why it matters": l["why_not_known"][:120], "suggested experiment": l["next_step"][:100]} for l in naive["leads"]]
        _top = mo.vstack([
            mo.md("# An LLM research assistant reads a NASA retina study"),
            mo.md(f"Dataset {naive['dataset']}: mice flown 35 days on the ISS. The assistant reports **{len(_rows)} findings**. "
                  "All confident. None checked. This is what you get when nothing in the loop can say no."),
            mo.ui.table(_rows, selection=None, page_size=15), reveal])
        if not reveal.value:
            slide1 = _top
        else:
            _kill = [{"reason": k["label"], "finding": k["claim"][:100], "the number that killed it": k["reason"][:140]} for k in naive["killed"]]
            _found = [(g, why) for g, why in _PAPER.items() if any(g in s.get("rows", []) for s in naive["survivors"])]
            _redisc = "".join(f"- **{g}**: {why}\n" for g, why in _found)
            slide1 = mo.vstack([_top,
                mo.md(f"## Helix: **{len(naive['killed'])} of {len(_rows)} findings killed**, {len(naive['survivors'])} survive"),
                mo.md("Code attached each finding's real numbers from the table. A separate critic judged every one and cites the number that decided it."),
                mo.ui.table(_kill, selection=None, page_size=15),
                mo.md("### And the survivors include what the scientists actually published\n"
                      "The scout never saw the paper. From the table alone it proposed, and the critic passed:\n" + _redisc)])
    return (slide1,)


@app.cell
def _(mo, html_file):
    slide2 = mo.vstack([mo.md("# How it works"), mo.Html(html_file("docs/helix-flow.html"))])
    return (slide2,)


@app.cell
def _(mo, load, os):
    _prod = load("results/product_OSD-421.json")
    def _padj(l):
        ps = [f["padj"] for f in l.get("table_facts", {}).values() if isinstance(f, dict) and "padj" in f]
        return f"{min(ps):.2g}" if ps else ""
    if _prod is None:
        slide3 = mo.md("_results/product_OSD-421.json missing._")
    else:
        _surv = [{"claim": s["claim"][:100], "why new": s["why_not_known"][:90], "next step": s["next_step"][:80], "padj": _padj(s), "critic": s["reason"][:100]} for s in _prod["survivors"]]
        _kill3 = [{"reason": k["label"], "claim": k["claim"][:100], "critic": k["reason"][:130], "padj": _padj(k)} for k in _prod["killed"]]
        slide3 = mo.vstack([
            mo.md("# The product: any table in, judged leads out"),
            mo.md(f"A different study, {_prod['dataset']} (thymus). **{len(_surv)} leads survive, {len(_kill3)} killed**, "
                  f"{_prod['seconds']} s, rules {os.path.basename(_prod['rules'])}. Live version: [localhost:2719](http://localhost:2719)."),
            mo.md("### Survivors"), mo.ui.table(_surv, selection=None, page_size=15),
            mo.md("### Killed, with the number"), mo.ui.table(_kill3, selection=None, page_size=15)])
    return (slide3,)


@app.cell
def _(mo, os, glob, json, difflib, html_file):
    _allv = sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))
    _versions, _seen = [], set()
    for _v in _allv:
        _t = open(_v).read()
        if _t not in _seen:
            _seen.add(_t); _versions.append(_v)
    def _meta(v):
        mp = v.replace(".md", ".meta.json"); return json.load(open(mp)) if os.path.exists(mp) else {}
    def _github_diff(lines):
        import html as _h
        style = {"+": "background:#e6ffec;color:#1a7f37", "-": "background:#ffebe9;color:#cf222e", "@": "background:#ddf4ff;color:#0550ae", " ": "color:#57606a"}
        rows = []
        for ln in lines:
            if ln.startswith(("+++", "---")): continue
            k = ln[:1] if ln[:1] in style else " "
            rows.append(f'<div style="{style[k]};display:flex;font:12.5px/1.5 ui-monospace,Menlo,monospace"><span style="width:1.4em;flex:none;text-align:center">{_h.escape(k.strip())}</span>'
                        f'<span style="white-space:pre-wrap;word-break:break-word">{_h.escape(ln[1:] if k != " " else ln)}</span></div>')
        return '<div style="border:1px solid #d0d7de;border-radius:6px;overflow:hidden;background:#fff;color:#1f2328">' + "".join(rows) + "</div>"
    _tabs = {}
    for _i, _v in enumerate(_versions):
        _name, _m = os.path.basename(_v), _meta(_v)
        _head = f"**{_name}**" + (f" · written by {_m['author']} · changed: {', '.join(_m['sections'])}" if _m else " · hand-written seed, 7 reasons to say no")
        if _i == 0:
            _tabs[_name] = mo.vstack([mo.md(_head), mo.md(open(_v).read())]); continue
        _prev = _versions[_i - 1]
        _d = difflib.unified_diff(open(_prev).read().splitlines(), open(_v).read().splitlines(), fromfile=os.path.basename(_prev), tofile=_name, lineterm="", n=1)
        _tabs[_name] = mo.vstack([mo.md(_head + f" · diff against {os.path.basename(_prev)}"), mo.Html(_github_diff(_d))])
    slide4 = mo.vstack([
        mo.md("# Does it learn? Every rewrite, scored on leads it never saw"),
        mo.Html(html_file("docs/helix-charts.html")),
        mo.md("## What each architect changed"), mo.ui.tabs(_tabs)])
    return (slide4,)


@app.cell
def _(mo, WB):
    _nasa = [{"set": "LLM holdout, 90 unseen leads", "v0": "27 mistakes", "v1": "21", "v2 (ships)": "18", "v4 (caught)": "23"},
            {"set": "OSD-255 retina paper, 34 claims", "v0": "0 false kills", "v1": "0", "v2 (ships)": "0", "v4 (caught)": "0"},
            {"set": "OSD-467 bone paper, 20 claims, never trained on", "v0": "0 false kills", "v1": "0", "v2 (ships)": "0", "v4 (caught)": "0"}]
    slide5 = mo.vstack([
        mo.md("# The proof is public"),
        mo.md("Every verdict is a Weave trace. Every rulebook version is a W&B artifact. Every version × lead set is a Weave Evaluation."),
        mo.hstack([mo.Html(f'<a href="{WB}/evaluations" target="_blank" style="display:inline-block;padding:12px 20px;background:#0f766e;color:#fff;border-radius:6px;font-weight:600;text-decoration:none">Open the Evals: v0 · v1 · v2 · v4</a>'),
                   mo.Html(f'<a href="{WB}/traces" target="_blank" style="display:inline-block;padding:12px 20px;background:#1c2126;color:#fff;border-radius:6px;font-weight:600;text-decoration:none">Open the Traces: 5,845 verdicts</a>')], justify="start"),
        mo.md("### Three sets, four rulebooks"), mo.ui.table(_nasa, selection=None),
        mo.md("**Zero published NASA findings killed, by any version.** Every unsupported claim killed with the number that decided it.")])
    return (slide5,)


@app.cell
def _(mo):
    slide6 = mo.vstack([mo.md("# Agents drift."), mo.md("## Usually a person notices, after trusting it."),
                        mo.md("## Here the loop noticed first, on data nobody tuned for, and the bad version never reached a user."),
                        mo.md("### Helix · built 12-13 Sep 2026 · Weave, W&B Inference, W&B Automations + ARIA, marimo")])
    return (slide6,)


@app.cell
def _(mo, slide1, slide2, slide3, slide4, slide5, slide6):
    mo.ui.tabs({"1 · The problem": slide1, "2 · How it works": slide2, "3 · The product": slide3,
                "4 · Does it learn?": slide4, "5 · The proof": slide5, "6 · Close": slide6})
    return


if __name__ == "__main__":
    app.run()
