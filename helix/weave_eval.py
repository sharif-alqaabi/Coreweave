"""Weave Evaluations: one evaluation per (labelled lead set, rules version), so the W&B Evals tab
can compare rules versions side by side with the same critic and the same scoring as loop.py.

    python3 scripts/weave_eval.py data/golden/nasa_OSD-467.json 0 4      # rules_v0 and rules_v4
    python3 scripts/weave_eval.py data/golden/holdout.json 0 4
    python3 scripts/weave_eval.py data/golden/holdout.json 4 --dry-run   # plumbing check, no LLM calls, scratch project

Dataset = the lead file's rows. Model = the critic with one rules version. Scorers = reason code
matches the label; kill/keep matches the label (false_kill = killed a lead labelled ok).
"""
import asyncio, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import weave
from helix.critic import Critic
from helix.critic_payload import Tables, build_payload

load_dotenv(".env")
FIELDS = ("id", "dataset", "shape", "claim", "why_not_known", "next_step", "rows", "table_facts", "label")
DRY = "--dry-run" in sys.argv                          # plumbing test: crude numeric critic, scratch project, no LLM calls
CRITIC, TABLES = Critic(dry_run=DRY), Tables(sorted(glob.glob("data/raw/*.csv")))


class CriticModel(weave.Model):
    rules_version: int

    @weave.op
    async def predict(self, id: str, dataset: str, claim: str, why_not_known: str, next_step: str, rows: list, table_facts: dict) -> dict:
        lead = {"id": id, "dataset": dataset, "claim": claim, "why_not_known": why_not_known,
                "next_step": next_step, "rows": rows, "table_facts": table_facts}
        payload = build_payload(lead, TABLES, rules_file=f"rules_v{self.rules_version}.md")
        return await asyncio.to_thread(CRITIC.judge, payload)      # sync critic, but examples run in parallel


@weave.op
def reason_match(label: str, output: dict) -> dict:
    return {"reason_correct": output["label"] == label}


@weave.op
def kill_match(label: str, output: dict) -> dict:
    human_kill, critic_kill = label != "ok", output["label"] != "ok"
    return {"kill_correct": human_kill == critic_kill, "false_kill": critic_kill and not human_kill,
            "missed_kill": human_kill and not critic_kill}


def main(lead_file, versions):
    weave.init(f"{os.environ['WANDB_ENTITY']}/{os.getenv('WANDB_PROJECT', 'helix')}{'-scratch' if DRY else ''}")
    tag = os.path.basename(lead_file)[:-5]
    rows = [{k: l.get(k, "") for k in FIELDS} for l in json.load(open(lead_file))]
    dataset = weave.Dataset(name=tag, rows=rows)
    for v in versions:
        ev = weave.Evaluation(name=f"critic-on-{tag}", dataset=dataset, scorers=[reason_match, kill_match],
                              evaluation_name=f"{tag} rules_v{v}")     # Evaluation name must differ from the Dataset name
        summary = asyncio.run(ev.evaluate(CriticModel(rules_version=int(v))))
        if DRY: print("raw summary:", json.dumps(summary, default=str)); continue
        rm, km = summary["reason_match"]["reason_correct"], summary["kill_match"]
        print(f"{tag} rules_v{v}: reason accuracy {rm['true_fraction']:.2f} | kill correct {km['kill_correct']['true_fraction']:.2f} "
              f"| false kills {km['false_kill']['true_count']} | missed kills {km['missed_kill']['true_count']}")


def cli():
    main(sys.argv[1], [a for a in sys.argv[2:] if not a.startswith("--")] or ["4"])
