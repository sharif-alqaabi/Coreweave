"""Helix as checkpointed state graphs (LangGraph). The nodes call the same functions loop.py and product.py already use;
what the graph adds is structure you can see, resume after a failure, fan-out for the architects, and a human approval
gate before a rulebook is promoted.

    python -m helix.orchestrate product data/raw/OSD-421_differential_expression.csv          # table -> judged -> verified -> linked
    python -m helix.orchestrate product data/raw/OSD-421_differential_expression.csv --use-saved --no-link
    python -m helix.orchestrate round --n 0 --dry-run                                         # one training round
    python -m helix.orchestrate round --n 3 --wait-for-aria 120 --approve                     # pause before promotion
    python -m helix.orchestrate resume --thread round-3                                        # a person approved: promote
    python -m helix.orchestrate mermaid                                                        # the graphs, as mermaid

Checkpoints: results/checkpoints.sqlite, one thread per run (product-<dataset>, round-<n>). A run that dies mid-way
resumes from its last completed node with the same command.
"""
from __future__ import annotations
import argparse, glob, json, operator, os, sys, time
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helix.settings import settings, ROOT

CHECKPOINTS = os.path.join(ROOT, "results", "checkpoints.sqlite")


def _log(state, msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")
    return {"log": [msg]}


# ============================================================ product: one table in, verified and linked findings out
class ProductState(TypedDict, total=False):
    csv_path: str
    dataset: str
    rules_path: str | None
    n_leads: int
    use_saved: bool
    link: bool
    summary: str
    leads: list
    judged: list
    survivors: list
    killed: list
    product_path: str
    verification: dict
    graph_stats: dict
    log: Annotated[list, operator.add]


def p_start(s: ProductState):
    dataset = os.path.basename(s["csv_path"]).split("_")[0]
    saved = os.path.join(ROOT, "results", f"product_{dataset}.json")
    out = {"dataset": dataset, "product_path": saved}
    if s.get("use_saved") or (not settings.llm_available() and os.path.exists(saved)):
        d = json.load(open(saved))
        out.update({"summary": d["summary"], "leads": d["leads"], "judged": d["leads"], "survivors": d["survivors"],
                    "killed": d["killed"], "rules_path": d["rules"]})
        out.update(_log(s, f"{dataset}: loaded the saved run ({len(d['survivors'])} survivors, {len(d['killed'])} killed)"
                           + ("" if s.get("use_saved") else "; no LLM key, so the scout and critic are skipped")))
    return out


def p_route(s: ProductState):
    return "verify" if s.get("judged") else "summarize"


def p_summarize(s: ProductState):
    from helix.summarize import summarize
    return {"summary": summarize(s["csv_path"]), **_log(s, "summarised the table (pandas)")}


def p_propose(s: ProductState):
    from helix.product import generate
    leads = generate(s["summary"], s["dataset"], s.get("n_leads", 60))
    return {"leads": leads, **_log(s, f"scout proposed {len(leads)} findings")}


def p_attach(s: ProductState):
    from helix.critic_payload import Table, enrich
    leads = enrich(s["leads"], Table(s["csv_path"]))
    return {"leads": leads, **_log(s, "attached the real numbers to every finding (pandas)")}


def p_judge(s: ProductState):
    from helix.critic import Critic
    from helix.critic_payload import Table
    from helix.product import best_rules
    rules = s.get("rules_path") or best_rules()
    verdicts = Critic().judge_all(s["leads"], Table(s["csv_path"]), rules)
    by_id = {l["id"]: l for l in s["leads"]}
    judged = [{**by_id[v["lead_id"]], "label": v["label"], "confidence": v["confidence"], "reason": v["reason"]} for v in verdicts]
    surv = [j for j in judged if j["label"] == "ok"]; kill = [j for j in judged if j["label"] != "ok"]
    json.dump({"dataset": s["dataset"], "summary": s["summary"], "rules": rules, "leads": judged, "survivors": surv, "killed": kill,
               "seconds": 0}, open(s["product_path"], "w"), indent=1)
    return {"judged": judged, "survivors": surv, "killed": kill, "rules_path": rules,
            **_log(s, f"critic with {os.path.basename(rules)}: {len(surv)} survive, {len(kill)} killed -> {s['product_path']}")}


def p_verify(s: ProductState):
    if not settings.typesafe_available():
        return _log(s, "no TYPESAFE_API_KEY: verification skipped")
    from helix.replicate import check_novelty
    out = check_novelty(s["product_path"], progress=lambda m: None)
    kinds = {}
    for l in out["leads"]:
        k = l["verdict"].split(":")[0].split(" in ")[0].split(" by ")[0]; kinds[k] = kinds.get(k, 0) + 1
    return {"verification": {"seconds": out["seconds"], "verdicts": kinds},
            **_log(s, f"TypeSafe verified {len(out['leads'])} survivors against {out['n_studies']} studies in {out['seconds']} s: {kinds}")}


def p_after_verify(s: ProductState):
    return "link" if s.get("link", True) and settings.typesafe_available() else END


def p_link(s: ProductState):
    from helix.graph import build as B
    B.main(["--no-explain"])
    st = json.load(open(B.OUT))["stats"]
    return {"graph_stats": st, **_log(s, f"research graph rebuilt: {st['nodes']['finding']} findings, {sum(v for k, v in st['edges'].items() if not k.endswith(':from'))} edges")}


def product_graph():
    g = StateGraph(ProductState)
    for name, fn in [("start", p_start), ("summarize", p_summarize), ("propose", p_propose), ("attach", p_attach),
                     ("judge", p_judge), ("verify", p_verify), ("link", p_link)]:
        g.add_node(name, fn)
    g.add_edge(START, "start")
    g.add_conditional_edges("start", p_route, {"summarize": "summarize", "verify": "verify"})
    g.add_edge("summarize", "propose"); g.add_edge("propose", "attach"); g.add_edge("attach", "judge"); g.add_edge("judge", "verify")
    g.add_conditional_edges("verify", p_after_verify, {"link": "link", END: END})
    g.add_edge("link", END)
    return g


# ============================================================ round: judge -> architects (fan-out) -> tournament -> approve -> promote
class RoundState(TypedDict, total=False):
    n: int
    train: str
    tables: list
    dry_run: bool
    wait_for_aria: int
    approve: bool
    group: str
    rules: str
    base: str
    acc: float
    prev_acc: float | None
    run_id: str | None
    misses: list
    candidates: Annotated[list, operator.add]
    winner: dict | None
    out: str
    log: Annotated[list, operator.add]


def _ctx(s: RoundState):
    """The objects loop.py's functions expect; rebuilt per node so a resumed run does not need pickled clients."""
    import loop
    from helix.critic import Critic
    from helix.critic_payload import Tables
    leads = json.load(open(s["train"]))
    table = Tables(s["tables"] or sorted(glob.glob(os.path.join(ROOT, "data/raw/*.csv"))))
    critic = Critic(dry_run=s.get("dry_run", False))
    args = SimpleNamespace(group=s.get("group", "helix-graph"), wait_for_aria=s.get("wait_for_aria", 0), patch_dir=None, dry_run=s.get("dry_run", False))
    return loop, leads, table, critic, args


def r_judge(s: RoundState):
    loop, leads, table, critic, args = _ctx(s)
    n = s["n"]
    run_id, result = loop.judge_phase(n, leads, table, critic, args)
    acc = result["metrics"]["screening/reason_accuracy"]
    prev = None
    prev_path = Path("results") / f"iter{n-1}.json"
    if n and prev_path.exists():
        prev = json.load(open(prev_path))["metrics"]["screening/reason_accuracy"]
    base = f"kit/critic/rules_v{n}.md"
    if prev is not None and acc < prev - loop.NOISE:
        base = f"kit/critic/rules_v{n-1}.md"
    return {"rules": f"kit/critic/rules_v{n}.md", "base": base, "acc": max(acc, prev or 0) if base != f"kit/critic/rules_v{n}.md" else acc,
            "prev_acc": prev, "run_id": run_id, "misses": result["misses"],
            **_log(s, f"round {n}: judged with rules_v{n}, reason accuracy {acc:.2f}, {len(result['misses'])} misses"
                      + (f"; rolled back to {os.path.basename(base)} as base" if base != f"kit/critic/rules_v{n}.md" else ""))}


def _architect(model):
    def node(s: RoundState):
        if s.get("dry_run"):
            return _log(s, f"architect {model.split('/')[-1]}: skipped (dry run)")
        loop, leads, table, critic, args = _ctx(s)
        tmp = Path("results/_candidates"); tmp.mkdir(parents=True, exist_ok=True)
        c = loop.candidate(model, s["misses"], s["base"], critic, table, leads, tmp)
        if not c:
            return _log(s, f"architect {model.split('/')[-1]}: no valid patch")
        c["misses"] = sorted(c["misses"])
        return {"candidates": [c], **_log(s, f"architect {model.split('/')[-1]}: patch scores {c['acc']:.2f} on train")}
    return node


def r_aria(s: RoundState):
    if not s.get("wait_for_aria") or not s.get("run_id") or s.get("dry_run"):
        return _log(s, "ARIA: not waited for")
    from helix.aria_channel import fetch_aria_patch
    from helix.reflect import render_patch
    from helix.evaluate import evaluate
    text = fetch_aria_patch(s["run_id"], s["n"], timeout_s=s["wait_for_aria"])
    if not text:
        return _log(s, f"ARIA: no patch within {s['wait_for_aria']} s")
    loop, leads, table, critic, args = _ctx(s)
    try:
        rendered, changed = render_patch(s["base"], text)
        path = "results/_candidates/rules_v800.md"; Path(path).write_text(rendered)
        r = evaluate(critic.judge_all(leads, table, path), leads)
        c = {"model": "ARIA", "patch": text, "sections": changed, "acc": r["metrics"]["screening/reason_accuracy"],
             "misses": sorted(m["hypothesis_id"] for m in r["misses"])}
        return {"candidates": [c], **_log(s, f"ARIA: patch scores {c['acc']:.2f} on train")}
    except ValueError as e:
        return _log(s, f"ARIA: patch rejected by guardrails ({e})")


def r_tournament(s: RoundState):
    cands = s.get("candidates", [])
    best = max(cands, key=lambda c: c["acc"], default=None)
    winner = best if best and best["acc"] > s["acc"] else None
    msg = (f"tournament: {len(cands)} candidates; " + (f"{winner['model'].split('/')[-1]} wins at {winner['acc']:.2f} > {s['acc']:.2f}"
                                                       if winner else f"none beat {s['acc']:.2f}; rules stay"))
    return {"winner": winner, **_log(s, msg)}


def r_gate(s: RoundState):
    """Human approval before promotion, when asked for: the run pauses here and resumes with Command(resume=True/False)."""
    if s.get("approve") and s.get("winner"):
        w = s["winner"]
        ok = interrupt({"question": f"Promote {w['model']}'s patch (train {w['acc']:.2f} vs {s['acc']:.2f}) to rules_v{s['n']+1}?",
                        "sections": w["sections"], "patch": w["patch"]})
        if not ok:
            return {"winner": None, **_log(s, "promotion declined by reviewer; rules copied forward unchanged")}
        return _log(s, "promotion approved by reviewer")
    return {}


def r_promote(s: RoundState):
    from helix.reflect import apply_patch
    n, base, w = s["n"], s["base"], s.get("winner")
    out = f"kit/critic/rules_v{n+1}.md"
    author = "none"
    if w:
        try:
            out = apply_patch(base, w["patch"], change_reason=f"iter {n} misses" + (" (rolled back)" if base != s["rules"] else ""),
                              author=w["model"].split("/")[-1], out_version=n + 1)
            author = w["model"].split("/")[-1]
        except ValueError as e:
            return {"out": out, **_log(s, f"patch rejected at apply time ({e}); rules unchanged")}
    if not Path(out).exists():
        Path(out).write_text(Path(base).read_text())
    return {"out": out, **_log(s, f"-> {out} (author={author})")}


def round_graph():
    g = StateGraph(RoundState)
    g.add_node("judge", r_judge)
    arch = [f"architect_{m.split('/')[-1].split('-')[0].lower()}" for m in settings.architects()]
    for name, model in zip(arch, settings.architects()):
        g.add_node(name, _architect(model))
    g.add_node("architect_aria", r_aria)
    g.add_node("tournament", r_tournament); g.add_node("approval", r_gate); g.add_node("promote", r_promote)
    g.add_edge(START, "judge")
    for name in arch + ["architect_aria"]:                          # fan-out: every architect proposes from the same misses
        g.add_edge("judge", name); g.add_edge(name, "tournament")
    g.add_edge("tournament", "approval"); g.add_edge("approval", "promote"); g.add_edge("promote", END)
    return g


# ============================================================ CLI
def _compile(graph):
    import sqlite3
    os.makedirs(os.path.dirname(CHECKPOINTS), exist_ok=True)
    conn = sqlite3.connect(CHECKPOINTS, check_same_thread=False)     # the fan-out nodes run on worker threads
    return graph.compile(checkpointer=SqliteSaver(conn))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("product"); p.add_argument("csv"); p.add_argument("--rules"); p.add_argument("--n-leads", type=int, default=60)
    p.add_argument("--use-saved", action="store_true"); p.add_argument("--no-link", action="store_true"); p.add_argument("--thread")
    r = sub.add_parser("round"); r.add_argument("--n", type=int, required=True); r.add_argument("--train", default="data/golden/train.json")
    r.add_argument("--table", nargs="*", default=None); r.add_argument("--dry-run", action="store_true"); r.add_argument("--wait-for-aria", type=int, default=0)
    r.add_argument("--approve", action="store_true", help="pause before promotion; continue with `resume --thread round-N`"); r.add_argument("--group", default="helix-graph")
    s = sub.add_parser("resume"); s.add_argument("--thread", required=True); s.add_argument("--decline", action="store_true")
    sub.add_parser("mermaid")
    a = ap.parse_args(argv)
    os.chdir(ROOT)
    if a.cmd == "mermaid":
        print("## Product pipeline\n\n```mermaid\n" + product_graph().compile().get_graph().draw_mermaid() + "```\n")
        print("## Training round\n\n```mermaid\n" + round_graph().compile().get_graph().draw_mermaid() + "```")
        return
    if a.cmd == "product":
        app = _compile(product_graph())
        thread = a.thread or f"product-{os.path.basename(a.csv).split('_')[0]}"
        final = app.invoke({"csv_path": a.csv, "rules_path": a.rules, "n_leads": a.n_leads, "use_saved": a.use_saved, "link": not a.no_link, "log": []},
                           config={"configurable": {"thread_id": thread}})
        print(f"done: thread {thread}; {len(final.get('survivors', []))} survivors, {len(final.get('killed', []))} killed"
              + (f"; verification {final['verification']['verdicts']}" if final.get("verification") else ""))
        return
    if a.cmd == "round":
        app = _compile(round_graph())
        thread = f"round-{a.n}"
        final = app.invoke({"n": a.n, "train": a.train, "tables": a.table or [], "dry_run": a.dry_run, "wait_for_aria": a.wait_for_aria,
                            "approve": a.approve, "group": a.group, "log": []}, config={"configurable": {"thread_id": thread}})
        if "__interrupt__" in final:
            q = final["__interrupt__"][0].value
            print(f"\nPAUSED for approval (thread {thread}): {q['question']}\n  sections: {q['sections']}\n"
                  f"  resume with: python -m helix.orchestrate resume --thread {thread}   (or --decline)")
        else:
            print(f"done: thread {thread} -> {final.get('out')}")
        return
    if a.cmd == "resume":
        app = _compile(round_graph())
        final = app.invoke(Command(resume=not a.decline), config={"configurable": {"thread_id": a.thread}})
        print(f"done: thread {a.thread} -> {final.get('out')}")


if __name__ == "__main__":
    main()
