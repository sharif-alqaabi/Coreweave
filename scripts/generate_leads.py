"""Scout: turn a dataset summary into leads.

    python3 scripts/generate_leads.py data/summaries/OSD-104.md ledger/leads.json

Uses agents/weave_scout/scout_prompt_60.md and helix.llm (W&B Inference by default).
Retries once if the model returns something that is not a JSON array.
"""
import json, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # repo root
from dotenv import load_dotenv
from helix import llm

load_dotenv(".env")
PROMPT = "agents/weave_scout/scout_prompt_60.md"
REQUIRED = {"id", "shape", "claim", "rows", "why_not_known", "next_step"}


def parse(text):
    m = re.search(r"\[.*\]", text, re.S)
    leads = json.loads(m.group()) if m else []
    return [l for l in leads if REQUIRED <= set(l)]


def main(summary_path, out_path):
    prompt = open(PROMPT).read() + "\n" + open(summary_path).read()
    for attempt in range(2):
        text = llm.chat("You output only a JSON array.", prompt, max_tokens=12000)
        leads = parse(text)
        if len(leads) >= 40:
            break
        print(f"attempt {attempt}: got {len(leads)} valid leads, retrying", file=sys.stderr)
    for i, l in enumerate(leads, 1):                       # normalise ids; the model sometimes skips
        l["id"] = f"lead_{i:03d}"
        l["dataset"] = summary_path.split("/")[-1].replace(".md", "")
    json.dump(leads, open(out_path, "w"), indent=1)
    print(f"{len(leads)} leads -> {out_path}")
    print("shapes:", dict(Counter(l["shape"] for l in leads)))
    print("genes cited:", sum(len(l["rows"]) for l in leads), "| leads with no rows:", sum(not l["rows"] for l in leads))


if __name__ == "__main__":
    main(*sys.argv[1:])
