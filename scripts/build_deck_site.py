"""Build app/deck_site.py: the demo deck with every input inlined (no file reads, no env, no helix
imports), so it can be exported as a static WebAssembly site and hosted anywhere.

    python3 scripts/build_deck_site.py
    marimo export html-wasm app/deck_site.py -o site --mode run
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(".env")


def padj(l):
    ps = [f["padj"] for f in l.get("table_facts", {}).values() if isinstance(f, dict) and "padj" in f]
    return f"{min(ps):.2g}" if ps else ""


def slim(l, keep):
    return {k: l.get(k, "") for k in keep}


naive = json.load(open("results/naive_OSD-255.json"))
prod = json.load(open("results/product_OSD-421.json"))
DATA = {
    "wb": f"https://wandb.ai/{os.getenv('WANDB_ENTITY', '')}/{os.getenv('WANDB_PROJECT', 'helix')}/weave",
    "naive": {"dataset": naive["dataset"], "rules": os.path.basename(naive["rules"]),
              "leads": [slim(l, ("claim", "why_not_known", "next_step", "rows")) for l in naive["leads"]],
              "killed": [slim(k, ("label", "claim", "reason")) for k in naive["killed"]],
              "survivor_rows": [s.get("rows", []) for s in naive["survivors"]]},
    "prod": {"dataset": prod["dataset"], "rules": os.path.basename(prod["rules"]), "seconds": prod["seconds"],
             "survivors": [{**slim(s, ("claim", "why_not_known", "next_step", "reason")), "padj": padj(s)} for s in prod["survivors"]],
             "killed": [{**slim(k, ("label", "claim", "reason")), "padj": padj(k)} for k in prod["killed"]]},
    "flow_html": open("docs/helix-flow.html").read().split("<style>", 1)[1].join(["<style>", ""]) if False else "<style>" + open("docs/helix-flow.html").read().split("<style>", 1)[1],
    "charts_html": "<style>" + open("docs/helix-charts.html").read().split("<style>", 1)[1],
    "rules": [],
}
seen = set()
for v in sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3])):
    t = open(v).read()
    if t in seen:
        continue
    seen.add(t)
    mp = v.replace(".md", ".meta.json")
    DATA["rules"].append({"name": os.path.basename(v), "text": t, "meta": json.load(open(mp)) if os.path.exists(mp) else {}})

src = open("app/deck.py").read()
# 1. replace the loader cell with an inlined-data cell
head, rest = src.split("@app.cell\ndef _():", 1)
_, rest = rest.split("    return mo, os, json, glob, difflib, WB, load, html_file\n", 1)
loader = f'''@app.cell
def _():
    import marimo as mo, os, json, difflib
    DATA = json.loads({json.dumps(json.dumps(DATA))})
    WB = DATA["wb"]
    return mo, os, json, difflib, DATA, WB


'''
src = head + loader + rest
# 2. slide 1: data from DATA
src = src.replace('def _(mo, load):\n    naive = load("results/naive_OSD-255.json")', 'def _(mo, DATA):\n    naive = DATA["naive"]')
src = src.replace('any(g in s.get("rows", []) for s in naive["survivors"])', 'any(g in rows for rows in naive["survivor_rows"])')
# 3. slide 2 and 4: html from DATA
src = src.replace('def _(mo, html_file):\n    slide2 = mo.vstack([mo.md("# How it works"), mo.Html(html_file("docs/helix-flow.html"))])',
                  'def _(mo, DATA):\n    slide2 = mo.vstack([mo.md("# How it works"), mo.Html(DATA["flow_html"])])')
# 4. slide 3: product from DATA (padj precomputed)
src = src.replace('def _(mo, load, os):\n    _prod = load("results/product_OSD-421.json")', 'def _(mo, DATA, os):\n    _prod = DATA["prod"]')
src = src.replace('"padj": _padj(s)', '"padj": s["padj"]').replace('"padj": _padj(k)', '"padj": k["padj"]')
src = src.replace('rules {os.path.basename(_prod[\'rules\'])}', 'rules {_prod[\'rules\']}')
# 5. slide 4: rules from DATA
i = src.index('def _(mo, os, glob, json, difflib, html_file):'); j = src.index('    _tabs = {}', i)
src = src[:i] + '''def _(mo, os, json, difflib, DATA):
    _versions = DATA["rules"]
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
''' + src[j:]
src = src.replace('''    for _i, _v in enumerate(_versions):
        _name, _m = os.path.basename(_v), _meta(_v)''', '''    for _i, _v in enumerate(_versions):
        _name, _m = _v["name"], _v["meta"]''')
src = src.replace('''            _tabs[_name] = mo.vstack([mo.md(_head), mo.md(open(_v).read())]); continue
        _prev = _versions[_i - 1]
        _d = difflib.unified_diff(open(_prev).read().splitlines(), open(_v).read().splitlines(), fromfile=os.path.basename(_prev), tofile=_name, lineterm="", n=1)
        _tabs[_name] = mo.vstack([mo.md(_head + f" · diff against {os.path.basename(_prev)}"), mo.Html(_github_diff(_d))])''',
'''            _tabs[_name] = mo.vstack([mo.md(_head), mo.md(_v["text"])]); continue
        _prev = _versions[_i - 1]
        _d = difflib.unified_diff(_prev["text"].splitlines(), _v["text"].splitlines(), fromfile=_prev["name"], tofile=_name, lineterm="", n=1)
        _tabs[_name] = mo.vstack([mo.md(_head + f" · diff against {_prev['name']}"), mo.Html(_github_diff(_d))])''')
src = src.replace('mo.Html(html_file("docs/helix-charts.html")),', 'mo.Html(DATA["charts_html"]),')
src = src.replace('"""Helix demo deck: the whole presentation in one browser tab.', '"""GENERATED by scripts/build_deck_site.py from app/deck.py: same deck, all data inlined, for the static site.\n\nHelix demo deck: the whole presentation in one browser tab.')
open("app/deck_site.py", "w").write(src)
print(f"app/deck_site.py written: {len(src)//1024} KB, {len(DATA['rules'])} rules versions, {len(DATA['naive']['leads'])} naive leads")
