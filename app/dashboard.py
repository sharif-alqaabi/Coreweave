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
