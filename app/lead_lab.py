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
    from helix import replicate
    return mo, os, json, tempfile, glob, Path, ROOT, run_pipeline, best_rules, replicate


@app.cell
def _(mo, best_rules, glob, os):
    versions, seen = [], set()                      # one entry per distinct rules text: the loop copies the
    for v in sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3])):   # base forward unchanged
        text = open(v).read()                       # when no candidate beats it, so v5..v8 can equal v4
        if text not in seen:
            seen.add(text); versions.append(v)
    mo.vstack([
        mo.md("# OSDR Lead Lab"),
        mo.md("Upload a NASA OSDR **differential expression** CSV (any of the 243 studies in `data/osdr_catalog.csv`). "
              "The pipeline summarizes it, proposes 60 hypotheses, attaches the true numbers, and judges every one "
              f"with the shipped rules, **{os.path.basename(best_rules())}**: the version with the best score on the 90 unseen "
              f"holdout leads, out of {len(versions)} distinct rulebooks the loop produced."),
    ])
    return (versions,)


@app.cell
def _(mo, versions, best_rules, os, glob):
    upload = mo.ui.file(filetypes=[".csv"], multiple=False, kind="area", max_size=500_000_000, label="Choose a *_differential_expression*.csv")
    best_text = open(best_rules()).read()          # best_rules() may name a copy (e.g. v6 == v4); pick the listed twin
    default = next((v for v in versions if open(v).read() == best_text), versions[-1])
    rules_pick = mo.ui.dropdown(options={os.path.basename(v): v for v in versions}, value=os.path.basename(default), label="Rules version")
    n_leads = mo.ui.slider(12, 60, value=60, step=12, label="Leads to propose")
    run = mo.ui.run_button(label="Run pipeline", kind="success")
    products = sorted(glob.glob("results/product_*.json"))                       # saved runs: show one without waiting 90 s
    product_pick = mo.ui.dropdown(options={os.path.basename(p)[8:-5]: p for p in products},
                                  value=os.path.basename(products[-1])[8:-5] if products else None, label="or show a saved run")
    mo.vstack([upload, mo.hstack([rules_pick, n_leads, run, product_pick], justify="start")])
    return upload, rules_pick, n_leads, run, product_pick


@app.cell
def _(mo, upload, rules_pick, n_leads, run, run_pipeline, tempfile, os, json):
    result = None
    if run.value and upload.value:
        f = upload.value[0] if isinstance(upload.value, (list, tuple)) and not hasattr(upload.value, "name") else upload.value
        name = f[0] if isinstance(f, tuple) and not hasattr(f, "name") else f.name        # (name, bytes) tuple or object
        data = f[1] if isinstance(f, tuple) and not hasattr(f, "contents") else f.contents
        tmp = os.path.join(tempfile.mkdtemp(prefix="leadlab-"), os.path.basename(name))
        open(tmp, "wb").write(data)
        with mo.status.spinner(title="Running the pipeline (about 90 s): summarize, propose, enrich, judge"):
            result = run_pipeline(tmp, rules_path=rules_pick.value, n_leads=n_leads.value, progress=lambda s: None)
        os.makedirs("results", exist_ok=True)                                    # saved like the CLI does, so the
        json.dump(result, open(f"results/product_{result['dataset']}.json", "w"), indent=1)   # novelty check can find it
    elif run.value:
        mo.stop(True, mo.md("_Upload a CSV first._"))
    return (result,)


@app.cell
def _(result, product_pick, json):
    # What the page shows: the run just made, else the saved run picked above.
    shown = result if result is not None else (json.load(open(product_pick.value)) if product_pick.value else None)
    return (shown,)


@app.cell
def _(mo, shown, novelty, os):
    if shown is None:
        out = mo.md("_Results appear here after a run._")
    else:
        def padj(lead):                             # smallest adjusted p-value among the genes the claim cites
            ps = [f["padj"] for f in lead.get("table_facts", {}).values() if isinstance(f, dict) and "padj" in f]
            return f"{min(ps):.2g}" if ps else ""     # pathway / global claims cite no single gene
        checked = {l["id"]: l["verdict"] for l in novelty["leads"]} if novelty and novelty["dataset"] == shown["dataset"] else {}
        rules = shown["rules"] if os.path.exists(shown["rules"]) else os.path.join("kit/critic", os.path.basename(shown["rules"]))  # saved on another machine
        surv = [{"lead": s["id"].split("_", 1)[1], "shape": s["shape"], "claim": s["claim"],
                 "OSDR check (TypeSafe)": checked.get(s["id"], "not checked yet"),
                 "why new": s["why_not_known"][:120], "next step": s["next_step"][:120], "padj": padj(s), "critic": s["reason"][:120]}
                for s in shown["survivors"]]
        kill = [{"lead": k["id"].split("_", 1)[1], "reason code": k["label"], "claim": k["claim"][:110], "critic": k["reason"][:140],
                 "padj": padj(k)} for k in shown["killed"]]
        out = mo.vstack([
            mo.md(f"## {shown['dataset']}: **{len(surv)} leads survive**, {len(kill)} killed "
                  f"(rules {os.path.basename(rules)}, {shown['seconds']} s)"),
            mo.md("### Survivors: hypotheses worth a scientist's time" +
                  ("  \n_**OSDR check** is TypeSafe's verification against every other OSDR dataset (section below); it does not change the critic's verdict._" if checked else "")),
            mo.ui.table(surv, selection=None, page_size=15),
            mo.md("### Killed, with the reason"), mo.ui.table(kill, selection=None, page_size=15),
            mo.accordion({"Dataset summary the scout read": mo.md("```\n" + shown["summary"] + "\n```"),
                          "Rules the critic applied": mo.md(open(rules).read())}),
        ])
    out
    return


@app.cell
def _(mo, shown):
    check = mo.ui.run_button(label="Verify with TypeSafe", kind="success", disabled=shown is None)
    mo.vstack([
        mo.md("---\n# Verification: the survivors against every other OSDR dataset"),
        mo.md("Every survivor says *why it is new*, usually \"not replicated in other spaceflight studies\". Nobody checks. "
              "This does, with **TypeSafe (Jev)**, a System One model that returns calibrated probabilities instead of prose. "
              "**Tier 1** scores how well each same-organism study in the 243-study catalog could replicate or refute the lead "
              "(no downloads); **Tier 2** looks the lead's genes up in every comparable table on disk and judges what the numbers "
              "say together. Direction and significance are arithmetic in pandas; Jev supplies the tissue judgment; the verdict is a code rule. "
              "It verifies the leads above; it does not generate or replace them."),
        check,
    ])
    return (check,)


@app.cell
def _(mo, shown, check, replicate, json, os):
    # Run on the button; otherwise show the last saved check for this dataset (instant on reload).
    novelty, note = None, ""
    if shown is not None:
        product = f"results/product_{shown['dataset']}.json"
        cached = f"results/replicate_{shown['dataset']}.json"
        if check.value:
            try:
                with mo.status.spinner(title="Jev is scoring every survivor against the catalog and the tables on disk (about 15 s)"):
                    novelty = replicate.check_novelty(product, progress=lambda s: None)
            except Exception as e:                      # no TYPESAFE_API_KEY, network: say so, keep the app up
                note = f"**Verification failed:** `{type(e).__name__}: {str(e)[:200]}`"
        elif os.path.exists(cached):
            novelty = json.load(open(cached)); note = f"_Showing the saved verification `{os.path.basename(cached)}` ({novelty['seconds']} s). Press the button to rerun._"
    mo.md(note) if note else None
    return (novelty,)


if __name__ == "__main__":
    app.run()
