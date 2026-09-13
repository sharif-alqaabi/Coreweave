"""Naive Lead Generator: the baseline Helix is measured against. Same scout, same table, but no numbers
attached and no critic, so every lead is presented as a finding. One button then runs Helix's critic on
those exact leads, live, so the audience watches most of them die.

    marimo run app/naive_lab.py -p 2720
"""
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo, os, sys, tempfile
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
    sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
    from helix.product import run_naive, judge_leads, best_rules
    return mo, os, tempfile, run_naive, judge_leads, best_rules


@app.cell
def _(mo):
    mo.md("# Research Assistant (naive)\\n\\nUpload a dataset. The assistant reads it and reports its findings. "
          "_This is the baseline: an LLM with no checks. Every claim below is unverified._")
    return


@app.cell
def _(mo):
    upload = mo.ui.file(filetypes=[".csv"], multiple=False, kind="area", max_size=500_000_000, label="Choose a *_differential_expression*.csv")
    run = mo.ui.run_button(label="Generate findings", kind="warn")
    mo.vstack([upload, run])
    return upload, run


@app.cell
def _(mo, upload, run, run_naive, tempfile, os):
    naive, csv_tmp = None, None
    if run.value and upload.value:
        f = upload.value[0] if isinstance(upload.value, (list, tuple)) and not hasattr(upload.value, "name") else upload.value
        name = f[0] if isinstance(f, tuple) and not hasattr(f, "name") else f.name
        data = f[1] if isinstance(f, tuple) and not hasattr(f, "contents") else f.contents
        csv_tmp = os.path.join(tempfile.mkdtemp(prefix="naive-"), os.path.basename(name))
        open(csv_tmp, "wb").write(data)
        with mo.status.spinner(title="Reading the dataset and writing findings (1 to 2 minutes)"):
            naive = run_naive(csv_tmp)
    return naive, csv_tmp


@app.cell
def _(mo, naive):
    if naive is None:
        findings_view = mo.md("_Findings appear here._")
    else:
        rows = [{"finding": l["claim"], "why it matters": l["why_not_known"][:140], "suggested experiment": l["next_step"][:120]} for l in naive["leads"]]
        findings_view = mo.vstack([mo.md(f"## {naive['dataset']}: **{len(rows)} findings**"),
                                   mo.ui.table(rows, selection=None, page_size=15)])
    findings_view
    return


@app.cell
def _(mo, naive):
    reveal = mo.ui.run_button(label="Now run Helix's critic on these", kind="success", disabled=naive is None)
    reveal
    return (reveal,)


@app.cell
def _(mo, naive, csv_tmp, reveal, judge_leads, os):
    if not (reveal.value and naive):
        reveal_view = mo.md("")
    else:
        with mo.status.spinner(title="Attaching the real numbers and judging every finding (about 60 s)"):
            r = judge_leads(naive["leads"], csv_tmp)
        kill = [{"reason": k["label"], "finding": k["claim"][:110], "critic": k["reason"][:150]} for k in r["killed"]]
        reveal_view = mo.vstack([
            mo.md(f"## Helix verdict: **{len(r['killed'])} of {len(naive['leads'])} findings killed**, "
                  f"{len(r['survivors'])} survive (rules {os.path.basename(r['rules'])})"),
            mo.md("Every kill cites the number from the table that decided it."),
            mo.ui.table(kill, selection=None, page_size=15)])
    reveal_view
    return


if __name__ == "__main__":
    app.run()
