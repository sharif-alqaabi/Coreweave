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
def _(mo, pd, refresh):
    refresh.value
    metrics = pd.read_csv("results/metrics.csv") if __import__("os").path.exists("results/metrics.csv") else pd.DataFrame()
    chart = mo.ui.altair_chart(
        __import__("altair").Chart(metrics).mark_line(point=True).encode(
            x="iteration:O", y=__import__("altair").Y("kill_precision:Q", scale={"domain": [0, 1]}),
            tooltip=["iteration", "kill_precision", "false_kill_rate", "misses"]).properties(height=260)
    ) if len(metrics) else mo.md("_No iterations yet. Run `python3 loop.py`._")
    chart
    return metrics, chart


@app.cell
def _(mo, json, glob, refresh):
    refresh.value
    files = sorted(glob.glob("results/iter*.json"), key=lambda p: int(p[12:-5]))
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
def _(mo, glob, os):
    versions = sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))
    tabs = {os.path.basename(v): mo.md(open(v).read()) for v in versions}
    mo.vstack([mo.md("## Rules versions"), mo.ui.tabs(tabs)])
    return


if __name__ == "__main__":
    app.run()
