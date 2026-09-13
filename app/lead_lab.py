"""OSDR Lead Lab: the product front end. Upload a NASA OSDR differential-expression CSV,
run the whole pipeline with the trained rules, read the judged leads.

    marimo run app/lead_lab.py

Based on the team's osdr_lead_lab.py; the "send to W&B" seam is replaced by helix.product.run_pipeline.
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo, os, sys, json, tempfile, glob
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
    sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
    from helix.product import run_pipeline, best_rules
    return mo, os, json, tempfile, glob, Path, ROOT, run_pipeline, best_rules


@app.cell
def _(mo, best_rules, glob, os):
    versions = sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))
    mo.vstack([
        mo.md("# OSDR Lead Lab"),
        mo.md("Upload a NASA OSDR **differential expression** CSV (any of the 243 studies in `data/osdr_catalog.csv`). "
              "The pipeline summarizes it, proposes 60 hypotheses, attaches the true numbers, and judges every one "
              f"with the trained rules (**{os.path.basename(best_rules())}**, learned over {len(versions)-1} revisions)."),
    ])
    return (versions,)


@app.cell
def _(mo, versions, best_rules, os):
    upload = mo.ui.file(filetypes=[".csv"], multiple=False, kind="area", max_size=500_000_000, label="Choose a *_differential_expression*.csv")
    rules_pick = mo.ui.dropdown(options={os.path.basename(v): v for v in versions}, value=os.path.basename(best_rules()), label="Rules version")
    n_leads = mo.ui.slider(12, 60, value=60, step=12, label="Leads to propose")
    run = mo.ui.run_button(label="Run pipeline", kind="success")
    mo.vstack([upload, mo.hstack([rules_pick, n_leads, run], justify="start")])
    return upload, rules_pick, n_leads, run


@app.cell
def _(mo, upload, rules_pick, n_leads, run, run_pipeline, tempfile, os):
    result = None
    if run.value and upload.value:
        f = upload.value[0] if isinstance(upload.value, list) else upload.value
        tmp = os.path.join(tempfile.mkdtemp(prefix="leadlab-"), f.name)
        open(tmp, "wb").write(f.contents)
        with mo.status.spinner(title="Running the pipeline (about 90 s): summarize, propose, enrich, judge"):
            result = run_pipeline(tmp, rules_path=rules_pick.value, n_leads=n_leads.value, progress=lambda s: None)
    elif run.value:
        mo.stop(True, mo.md("_Upload a CSV first._"))
    return (result,)


@app.cell
def _(mo, result, os):
    if result is None:
        out = mo.md("_Results appear here after a run._")
    else:
        surv = [{"lead": s["id"].split("_", 1)[1], "shape": s["shape"], "claim": s["claim"], "why new": s["why_not_known"][:120],
                 "next step": s["next_step"][:120], "confidence": s["confidence"], "critic": s["reason"][:120]} for s in result["survivors"]]
        kill = [{"lead": k["id"].split("_", 1)[1], "reason code": k["label"], "claim": k["claim"][:110], "critic": k["reason"][:140],
                 "confidence": k["confidence"]} for k in result["killed"]]
        out = mo.vstack([
            mo.md(f"## {result['dataset']}: **{len(surv)} leads survive**, {len(kill)} killed "
                  f"(rules {os.path.basename(result['rules'])}, {result['seconds']} s)"),
            mo.md("### Survivors: hypotheses worth a scientist's time"), mo.ui.table(surv, selection=None, page_size=15),
            mo.md("### Killed, with the reason"), mo.ui.table(kill, selection=None, page_size=15),
            mo.accordion({"Dataset summary the scout read": mo.md("```\n" + result["summary"] + "\n```"),
                          "Rules the critic applied": mo.md(open(result["rules"]).read())}),
        ])
    out
    return


if __name__ == "__main__":
    app.run()
