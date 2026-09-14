"""A DSPy baseline for the critic: is a tournament of LLM architects better than a standard prompt optimiser?

The architects rewrite a plain-text rulebook from the critic's misses and are gated on train, then holdout. DSPy's
optimisers do the same job with a different mechanism: they search over instructions and few-shot demonstrations for a
fixed program, scored by a metric on the same train set. Running both on the same splits answers the question with a
number, and the holdout gate applies to DSPy exactly as it applies to the tournament.

    python -m helix.dspy_baseline --dry-run                         # load the splits, build the program, no model calls
    python -m helix.dspy_baseline --optimizer bootstrap --max-demos 8   # needs an LLM key (LITELLM_MODEL or the W&B route)
    python -m helix.dspy_baseline --optimizer mipro --auto light

Writes results/dspy_<optimizer>.json: train and holdout reason accuracy, false kills, and the optimised program, so the
row can sit next to rules_v0 / v2 / v4 in the results table.
"""
from __future__ import annotations
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helix.settings import settings, ROOT
from helix.critic_payload import OPTIONS

RESULTS = os.path.join(ROOT, "results")


def _facts(lead):
    """The numbers the critic sees, without per-sample lists."""
    return {g: {k: v for k, v in f.items() if k in ("log2fc", "padj", "higher_group", "carriers", "mean_count", "error", "significant", "up", "down")}
            for g, f in lead.get("table_facts", {}).items() if isinstance(f, dict)}


def examples(path):
    import dspy
    out = []
    for l in json.load(open(path)):
        gold = l.get("label") or l.get("human_label") or l.get("gold_label")
        if gold not in OPTIONS:
            continue
        out.append(dspy.Example(claim=l["claim"], why_not_known=l.get("why_not_known", ""), next_step=l.get("next_step", ""),
                                numbers=json.dumps(_facts(l)), label=gold).with_inputs("claim", "why_not_known", "next_step", "numbers"))
    return out


def build_program():
    import dspy

    class Critique(dspy.Signature):
        """Judge one research finding against the real numbers attached by code. Choose exactly one label:
        ok (numbers support it, not textbook, has a concrete next step); contradicted (numbers disagree: wrong direction, padj above 0.05,
        gene absent); underpowered (very low counts or borderline padj with few carriers); confound (signal from a minority of samples);
        already_known (a textbook result restated); untestable (no falsifiable proposition or no next step); no_mechanism (real change,
        no biological account). Trust the numbers over the claim's own figures."""
        claim: str = dspy.InputField()
        why_not_known: str = dspy.InputField(desc="the proposer's argument that this is new")
        next_step: str = dspy.InputField()
        numbers: str = dspy.InputField(desc="JSON: per cited gene, log2fc, padj, higher_group, carriers, mean_count")
        label: str = dspy.OutputField(desc="one of: " + ", ".join(OPTIONS))
        reason: str = dspy.OutputField(desc="one sentence citing a number")

    class CriticProgram(dspy.Module):
        def __init__(self):
            super().__init__()
            self.judge = dspy.ChainOfThought(Critique)

        def forward(self, claim, why_not_known, next_step, numbers):
            out = self.judge(claim=claim, why_not_known=why_not_known, next_step=next_step, numbers=numbers)
            lab = (out.label or "").strip().lower()
            out.label = lab if lab in OPTIONS else "ok"
            return out
    return CriticProgram()


def metric(example, pred, trace=None):
    return float(example.label == pred.label)


def score(program, exs):
    """Reason accuracy and false kills, the same two numbers the loop reports."""
    right = kills_wrong = 0
    for ex in exs:
        p = program(claim=ex.claim, why_not_known=ex.why_not_known, next_step=ex.next_step, numbers=ex.numbers)
        right += p.label == ex.label
        kills_wrong += (ex.label == "ok" and p.label != "ok")
    return {"reason_accuracy": round(right / len(exs), 3), "false_kills": kills_wrong, "n": len(exs)}


def configure_lm():
    import dspy
    model = settings.litellm_model
    kw = {}
    if not model:
        if settings.wandb_api_key:
            model = f"openai/{settings.wandb_model}"
            proj = settings.wandb_entity_project or f"{settings.wandb_entity}/{settings.wandb_project}"
            kw = {"api_base": settings.WANDB_INFERENCE, "api_key": settings.wandb_api_key, "extra_headers": {"OpenAI-Project": proj}}
        elif settings.anthropic_api_key:
            model = f"anthropic/{settings.anthropic_model}"
        elif settings.openai_api_key:
            model = f"openai/{settings.openai_model}"; kw = {"api_base": settings.openai_base_url, "api_key": settings.openai_api_key}
        else:
            raise SystemExit("no LLM key: set WANDB_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY or LITELLM_MODEL in .env")
    dspy.configure(lm=dspy.LM(model, temperature=0.0, max_tokens=600, **kw))
    return model


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", default=os.path.join(ROOT, "data/golden/train.json"))
    ap.add_argument("--holdout", default=os.path.join(ROOT, "data/golden/holdout.json"))
    ap.add_argument("--optimizer", choices=["none", "bootstrap", "mipro"], default="bootstrap")
    ap.add_argument("--max-demos", type=int, default=8)
    ap.add_argument("--auto", choices=["light", "medium", "heavy"], default="light")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    import dspy
    train, holdout = examples(a.train), examples(a.holdout)
    program = build_program()
    print(f"train {len(train)} examples, holdout {len(holdout)}; program: ChainOfThought(Critique) -> label, reason")
    if a.dry_run:
        print("dry run: splits load and the program compiles; no model calls"); return
    model = configure_lm(); t0 = time.time()
    before = score(program, holdout)
    print(f"{model}: unoptimised holdout {before}")
    if a.optimizer == "bootstrap":
        opt = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=a.max_demos, max_labeled_demos=a.max_demos)
        program = opt.compile(program, trainset=train)
    elif a.optimizer == "mipro":
        opt = dspy.MIPROv2(metric=metric, auto=a.auto)
        program = opt.compile(program, trainset=train, requires_permission_to_run=False)
    after_train, after_hold = score(program, train), score(program, holdout)
    print(f"{a.optimizer}: train {after_train} | holdout {after_hold} | {time.time()-t0:.0f} s")
    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, f"dspy_{a.optimizer}.json")
    program.save(os.path.join(RESULTS, f"dspy_{a.optimizer}_program.json"))
    json.dump({"model": model, "optimizer": a.optimizer, "holdout_before": before, "train": after_train, "holdout": after_hold,
               "reference": {"rules_v0_holdout": 0.60, "rules_v2_holdout": 0.73, "rules_v4_holdout": 0.64}, "seconds": round(time.time() - t0)},
              open(out, "w"), indent=1)
    print("->", out)


if __name__ == "__main__":
    main()
