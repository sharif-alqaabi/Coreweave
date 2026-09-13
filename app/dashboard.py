"""Helix dashboard (marimo). Run:  marimo run app/dashboard.py

Reads results/metrics.csv and results/iter*.json written by loop.py. Refreshes every 5 s.
"""
import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo, pandas as pd, json, glob, os
    return mo, pd, json, glob, os


@app.cell
def _(mo):
    refresh = mo.ui.refresh(default_interval="5s")
    mo.vstack([mo.md("# Helix: kill precision across iterations"), refresh])
    return (refresh,)


@app.cell
def _(mo, pd, refresh, json, glob):
    refresh.value
    metrics = pd.read_csv("results/metrics.csv") if __import__("os").path.exists("results/metrics.csv") else pd.DataFrame()
    alt = __import__("altair")
    long = metrics.melt(id_vars=["iteration"], value_vars=["reason_accuracy", "kill_precision"],
                        var_name="metric", value_name="value") if len(metrics) else metrics
    chart = mo.ui.altair_chart(
        alt.Chart(long).mark_line(point=True).encode(
            x="iteration:O", y=alt.Y("value:Q", scale={"domain": [0, 1]}), color="metric:N",
            tooltip=["iteration", "metric", "value"]).properties(height=260)
    ) if len(metrics) else mo.md("_No iterations yet. Run `python3 loop.py`._")
    hold, n_hold = {}, 0
    for p in sorted(glob.glob("results/holdout_rules_v*.json"), key=lambda p: int(p.split("_v")[-1][:-5])):
        h = json.load(open(p)); hold[h["rules"].split("/")[-1]] = h["metrics"]; n_hold = h.get("n", 0)
    hold_md = mo.md(f"**Holdout ({n_hold} leads never seen by the loop):** " + " | ".join(
        f"{k}: reason accuracy {v['screening/reason_accuracy']:.2f}, kill recall {v['screening/kill_recall']:.2f}, "
        f"kill precision {v['screening/kill_precision']:.2f}" for k, v in hold.items())) if hold else mo.md("_Holdout not run yet._")
    mo.vstack([chart, hold_md])
    return metrics, chart


@app.cell
def _(mo, json, glob, refresh):
    refresh.value
    files = sorted([f for f in glob.glob("results/iter*.json") if ".run." not in f], key=lambda p: int(p[12:-5]))
    latest = json.load(open(files[-1])) if files else {"verdicts": [], "misses": []}
    survivors = [v for v in latest["verdicts"] if v["label"] == "ok"]
    mo.vstack([
        mo.md(f"## Iteration {len(files)-1 if files else '-'}: {len(survivors)} survivors, {len(latest['misses'])} misses"),
        mo.ui.table(survivors, selection=None) if survivors else mo.md("_none_"),
        mo.md("### Misses (critic vs human)"),
        mo.ui.table([{k: m[k] for k in ("hypothesis_id", "human_reason_code", "critic_reason_code", "critic_reason")}
                     for m in latest["misses"]], selection=None) if latest["misses"] else mo.md("_none_"),
    ])
    return


@app.cell
def _(mo, glob, os, json):
    import difflib
    allv = sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))
    versions, seen = [], set()                    # distinct rulebooks only; the loop copies a base forward when nothing wins
    for v in allv:
        t = open(v).read()
        if t not in seen:
            seen.add(t); versions.append(v)
    def github_diff(lines):
        """Unified diff -> GitHub-style HTML: green rows added, red rows removed, gutter with + / -."""
        import html as _h
        style = {"+": "background:#e6ffec;color:#1a7f37", "-": "background:#ffebe9;color:#cf222e",
                 "@": "background:#ddf4ff;color:#0550ae", " ": "color:#57606a"}
        rows = []
        for ln in lines:
            if ln.startswith(("+++", "---")):
                continue
            k = ln[:1] if ln[:1] in style else " "
            rows.append(f'<div style="{style[k]};display:flex;font:12.5px/1.5 ui-monospace,Menlo,monospace">'
                        f'<span style="width:1.4em;flex:none;text-align:center;user-select:none">{_h.escape(k.strip())}</span>'
                        f'<span style="white-space:pre-wrap;word-break:break-word">{_h.escape(ln[1:] if k != " " else ln)}</span></div>')
        return ('<div style="border:1px solid #d0d7de;border-radius:6px;overflow:hidden;background:#fff;color:#1f2328">'
                + "".join(rows) + "</div>")
    def meta(v):
        mp = v.replace(".md", ".meta.json")
        return json.load(open(mp)) if os.path.exists(mp) else {}
    tabs = {}
    for i, v in enumerate(versions):
        name, m = os.path.basename(v), meta(v)
        head = f"**{name}**" + (f" · author {m['author']} · changed {', '.join(m['sections'])}" if m else " · hand-written seed")
        if i == 0:
            tabs[name] = mo.vstack([mo.md(head), mo.md(open(v).read())])
            continue
        prev = versions[i - 1]
        diff = difflib.unified_diff(open(prev).read().splitlines(), open(v).read().splitlines(),
                                    fromfile=os.path.basename(prev), tofile=name, lineterm="", n=1)
        tabs[name] = mo.vstack([mo.md(head + f" · diff against {os.path.basename(prev)}"),
                                mo.Html(github_diff(diff)),
                                mo.accordion({"full text": mo.md(open(v).read())})])
    charts = open("docs/helix-charts.html").read()
    charts = charts[charts.index("<style>"):]                       # drop the <title>; keep style + markup
    mo.vstack([mo.md("## Rules versions: what each rewrite did to the score"), mo.Html(charts),
               mo.md("## Rules versions: what each architect changed"), mo.ui.tabs(tabs)])
    return


if __name__ == "__main__":
    app.run()
