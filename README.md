# Helix

**A self-improving multi-agent loop that combs NASA OSDR data, finds gene-expression leads, kills the bad ones, and rewrites its own playbook every iteration.**

<p align="center">
<img src="https://img.shields.io/badge/status-hackathon-ff6b35?style=for-the-badge" alt="hackathon" />
<img src="https://img.shields.io/badge/loop-self--evolving-7c5cff?style=for-the-badge" alt="self-evolving" />
<img src="https://img.shields.io/badge/domain-NASA%20OSDR-00c2a8?style=for-the-badge" alt="nasa osdr" />
<img src="https://img.shields.io/badge/observability-W%26B%20Weave-ffbe0b?style=for-the-badge" alt="weave" />
<img src="https://img.shields.io/badge/ui-Marimo-ff4d6d?style=for-the-badge" alt="marimo" />
</p>

<p align="center">
<strong>Ingest → Scout → Critique → Score against gold → Evolve → Repeat</strong><br/>
<em>Leads that survive the critic hit the ledger. Skills that miss the golden set get rewritten by Aria.</em>
</p>

---

## Why this exists

NASA OSDR is dense, noisy, and full of almost-signals. Flight vs. ground. Microgravity vs. 1g. A contrast table with 20,000 genes and three papers that almost say the same thing. Humans miss leads because they cannot read every OSDR study, DE table, and methods section at once. Naive LLM agents invent leads because nothing is allowed to say **no**.

Helix is a closed loop with jobs that should never live in the same model:

```
| Role          | Agent / layer      | Job                                                                                          |
| :------------ | :----------------- | :------------------------------------------------------------------------------------------- |
| **Prep**      | Python DGE script  | Isolate differential gene expression from NASA datasets before anyone starts narrating.      |
| **Scout**     | LLM                | Read OSDR papers + DE tables. Propose leads. Translate stats into plain English.             |
| **Nervous system** | **W&B Weave** | Trace every claim, tool call, token, and verdict. No lead without a trace id.                |
| **Critic**    | Separate LLM       | Attempt to kill leads. Demand evidence. Score survival.                                      |
| **Architect** | **Aria**           | Compare this iteration's leads to a golden set. Patch rules / skills / tools toward 100%.    |
| **Stage**     | **Marimo**         | Chat the loop, watch the curve, inspect the ledger.                                          |
```

The point is not “an agent that finds hypotheses.” The point is an agent that **gets better at finding the same leads a careful analyst would keep** — because the loop is observable, adversarial, and scored against gold.

Yes — this is plausible. The hard parts are discipline, not magic: keep generation and judgment in different models, log everything in Weave, and let Aria mutate the toolkit instead of vibing a new system prompt.

---

## The v1 model

```text
 NASA datasets / papers
            │
            ▼
  python script to isolate
  differential gene expression
            │
            ▼
   ┌────────────────────────────────┐
   │  OSDR paper + LLM + DE data    │
   │  Scout:                        │
   │   - read datasets              │
   │   - generate leads             │
   │   - interpret into plain English│
   └───────────┬────────────────────┘
               │          ▲
               │          │  new rules / skills / tools
               ▼          │
         critic:          │
         attempts to      │
         kill leads       │
               │          │
               ▼          │
         Aria:            │
         compare leads ───┘
         to golden set
         suggest patches
         toward 100% accuracy

               │
               ▼
        ┌──────────────────────────┐
        │     Marimo interface     │
        │  chatbot │ chart │ leads │
        └──────────────────────────┘

        Weave sits under the loop:
        every span, every lead, every kill.
```

1. **Prep** pulls NASA / OSDR sources and runs a Python contrast so the scout starts from real DE genes, not a PDF vibe.
2. **Scout** reads the paper + the isolated table, writes cited, falsifiable leads in plain English, and emits a full Weave trace.
3. **Critic** never generates. It only rejects, demotes, or conditionally promotes. Survival requires evidence, novelty, and a testable next step.
4. **Aria** does not hunt papers. It hunts *misses against the golden set*: which leads gold kept and we killed, which leads we kept and gold never would, which skills wasted tokens. Then it ships a patch into the next kit.
5. **Marimo** is the cockpit — chat with the scout, watch iteration curves, flip through the ledger.

Every cycle should leave behind a tighter scout, not just a longer list of ideas.

---

## Agents in detail

### Prep — differential expression first

Spaceflight RNA-seq is not a chat problem until it is a table problem.

- Ingest NASA OSDR studies and companion papers.
- Isolate the contrast that matters (flight vs. ground, tissue, timepoint, strain).
- Emit a typed DE artifact: gene, log2FC, p / q, direction, sample metadata.
- That artifact is what the scout is allowed to cite. No table id, no lead.

### Scout — OSDR paper + LLM + data

The working scientist. Reads corpora, DE tables, and methods. Writes leads. Talks like a human.

- Reads OSDR studies, figures-as-text, and the isolated DE table.
- Proposes **leads**: short, cited, falsifiable claims with a suggested follow-up.
- Interprets the contrast in plain English (“this gene went up in flight, survived multiple-testing, and the paper’s discussion never names it”).
- Logs every step into W&B Weave: sessions, turns, tool calls, tokens, latency, cost, and lead objects as first-class artifacts.

A lead that cannot be traced is not a lead. It is a vibe.

```text
Lead
├── claim
├── evidence[]          # OSDR study / table / gene rows / paper span
├── confidence
├── novelty vs prior ledger
├── suggested experiment or re-analysis
└── weave_trace_id      # mandatory
```

### Critic — the shutdown valve

A different model, different prompt, different incentives.

The critic is paid to be unimpressed. Its only job, per the v1 sketch: **attempt to kill leads.**

```
| Verdict      | Meaning                                                 |
| :----------- | :------------------------------------------------------ |
| **Kill**     | Unsupported, circular, already known, or untestable.    |
| **Park**     | Interesting but under-evidenced. Do not promote.        |
| **Survive**  | Cited, novel enough, and has a cheap next measurement.  |
| **Escalate** | High-value; needs a human or a heavier tool next round. |
```

Typical kill reasons the critic is required to name:

- claim does not follow from the cited DE rows
- lead restates a textbook space-biology result as a discovery
- no operational next step
- tool output was treated as ground truth without a sanity check
- same lead already died last iteration
- gene did not actually pass the contrast filter the prep script emitted

Survivors go on the **ledger**. Everything else is still logged — failures are training data for Aria.

### Aria — loop architect, scored against gold

Aria evaluates the *system*, not the biology.

After each iteration it reads:

- Weave traces and cost curves
- critic verdicts and disagreement cases
- which tools were called, which returned garbage
- which rules the scout ignored
- **this iteration’s leads vs. a golden set**

Then it writes a patch set whose explicit target is **100% accuracy against gold** — meaning: recover every gold lead, mint zero junk the gold set would reject.

```
| Artifact   | What Aria may mint                                                                                         |
| :--------- | :--------------------------------------------------------------------------------------------------------- |
| **Rules**  | Hard constraints (“never propose a lead without an OSDR table id and a gene that passed q < 0.05”).        |
| **Skills** | Playbooks (“read an RNA-seq contrast and extract only statistically backed flight-vs-ground leads”).       |
| **Tools**  | New or revised functions (schema validators, duplicate-lead detectors, cheap statistical screens).         |
```

Aria’s output is versioned. If a patch drops agreement with gold, roll it back. The loop is allowed to evolve; it is not allowed to forget what used to work.

### Marimo — the interface

Judges and scientists should not have to tail JSONL.

```
┌─────────────────────────────────────────────┐
│              Marimo interface               │
│  ┌──────────┐   ┌──────────┐   ┌─────────┐  │
│  │ chatbot  │   │  curve   │   │  leads  │  │
│  │ ask the  │   │ survive  │   │ ledger  │  │
│  │ scout,   │   │ rate vs  │   │ kill /  │  │
│  │ inspect  │   │ gold,    │   │ park /  │  │
│  │ a trace  │   │ cost     │   │ survive │  │
│  └──────────┘   └──────────┘   └─────────┘  │
└─────────────────────────────────────────────┘
```

- **Chatbot** — interrogate a study, a gene, a killed lead, a Weave trace.
- **Chart** — iteration yield, critic kill-rate, gold agreement, token cost.
- **Leads** — the living ledger, filterable by verdict and iteration.

---

## Why the three-way split

One agent that both dreams and grades will grade generously.

```text
same model → eloquent nonsense survives
split models → eloquence is not evidence
```

```
| Coupling                            | Failure mode                                      |
| :---------------------------------- | :------------------------------------------------ |
| Scout + critic in one LLM           | Self-justifying leads                             |
| No DE prep                          | The model narrates genes that never moved         |
| No telemetry                        | You cannot tell *why* a lead appeared             |
| No golden set                       | Aria optimizes for “sounds science-y”             |
| No Aria                             | The prompt rots; the same mistakes replay forever |
| Aria edits science instead of tools | The architect starts hallucinating biology        |
```

Helix keeps generation, judgment, and meta-improvement on separate seats. Weave is instrumented so Aria has receipts, not vibes. Gold is the scoreboard so “better” means something you can plot in Marimo.

---

## What “a lead” means here

Not a paragraph. A structured object that can die cleanly.

```json
{
  "id": "lead_0841",
  "iteration": 7,
  "claim": "Gene X upregulation co-occurs with pathway Y only in flight cohort Z under condition T.",
  "evidence": [
    {"source": "OSDR:OSD-XXX", "artifact": "table_de_results", "rows": ["X"]},
    {"source": "pmid:12345678", "quote_span": "…"}
  ],
  "why_not_known": "Prior reviews cover Y on the ground, not the T × flight interaction.",
  "next_step": "Recompute the contrast with batch covariate B; check if X remains at q < 0.05.",
  "critic": {"verdict": "survive", "score": 0.74},
  "gold": {"in_golden_set": true, "match": "exact"},
  "trace": "weave://project/helix/call/..."
}
```

The ledger is the product. Papers, Marimo dashboards, and follow-up experiments are downstream of a ledger that has already been attacked.

---

## Architecture (hackathon shape)

```text
helix/
├── agents/
│   ├── scout/          # OSDR + DE table → leads in plain English
│   ├── critic/         # verdict-only judge
│   └── aria/           # gold comparison + kit patch writer
├── prep/
│   └── dge.py          # isolate differential expression from NASA data
├── kit/                # living toolkit Aria mutates
│   ├── rules/
│   ├── skills/
│   └── tools/
├── gold/               # golden lead set for the current shard
├── ledger/             # surviving + killed leads
├── traces/             # W&B Weave project
├── ui/
│   └── app.py          # Marimo: chatbot + chart + leads
└── loop.py             # one iteration = prep → scout → critic → aria → swap kit
```

**One iteration**

1. Run `prep/dge.py` on the current OSDR shard. Emit the contrast table.
2. Load current `kit/` (rules, skills, tools).
3. Run Scout over paper + table. Emit leads + Weave traces.
4. Run Critic over each lead. Write verdicts to the ledger.
5. Run Aria: diff ledger vs `gold/`, mine traces, propose a kit patch.
6. Validate the diff (schema, tests, rollback plan).
7. Promote the new kit. Bump iteration. Refresh Marimo.

Keep iteration cheap. A loop that cannot finish in minutes will not get enough generations to evolve.

---

## Observability is not optional

W&B Weave is the nervous system:

- every scout tool call is a span
- every lead is an object with a parent trace
- every critic verdict is feedback on that object
- every Aria patch is a versioned artifact tied to the iteration that produced it
- gold agreement is an eval, not a vibe

If you cannot answer “which skill caused this bad lead?”, Aria is guessing. If Aria is guessing, the loop is theater.

**Evals tab.** `python3 scripts/weave_eval.py data/golden/<set>.json 0 4` publishes each labelled lead set as a Weave Dataset and runs the critic over it once per rules version as a Weave Evaluation (`helix/weave_eval.py`). Two scorers: reason code matches the label, and kill/keep matches the label with false kills counted. Same critic, same rules files, same numbers as `loop.py --holdout`; the Compare button puts rules v0 next to v4 per lead. `--dry-run` uses the numeric fallback critic in a scratch project to check the wiring without spending model calls.

---

## Plausibility notes

What is already real:

- OSDR studies with companion papers and downloadable expression matrices
- Multi-agent scientific workflows that separate literature, analysis, and review
- Trace-first agent stacks (W&B Weave sessions, turns, tools, evals)
- Skill files and tool registries that an agent can rewrite between runs
- Adversarial judges that raise precision on generated hypotheses
- Marimo as a reactive cockpit for agents + plots + tables

What this project has to prove in a hackathon window:

- A DE-first ingest that the scout is not allowed to ignore
- A lead schema strict enough to kill slop automatically
- A critic that does not rubber-stamp the scout
- An Aria step that emits *executable* kit changes after a gold comparison, not advice
- A Marimo view where a judge can watch agreement-with-gold move across three iterations

What we are not claiming:

- Autonomous discovery of a Nature paper by Sunday
- Replacing wet lab, statisticians, or NASA data curators
- That Aria should have write access to OSDR
- That “100% accuracy” is a moral victory rather than a scoring target on a frozen gold set

---

## Success criteria

A demo is winning if judges can watch **three iterations** in Marimo and see the system change its own behavior.

```
| Signal    | Good                                              | Bad                                    |
| :-------- | :------------------------------------------------ | :------------------------------------- |
| Yield     | Fewer proposals, more survivors, closer to gold   | More proposals, same junk              |
| Critic    | Named kill reasons, stable rubric                 | “Looks good” / “not sure”              |
| Aria      | Diff in `kit/` that Scout actually loads          | A paragraph of suggestions             |
| Gold      | Precision + recall vs gold both move the right way| Optimize one, torch the other          |
| Telemetry | Every lead has a Weave trace id                   | Screenshots of a chat                  |
| UI        | Chat + curve + ledger in one Marimo app           | “please run this notebook locally”     |
| Safety    | Kit changes are reviewed / test-gated             | Silent prompt injection into the scout |
```

---

## Roadmap

**V0 — weekend spine**
- [ ] Lead schema + ledger
- [ ] Python DGE isolation on one OSDR study
- [ ] Scout on paper + one DE table
- [ ] Critic with kill / park / survive
- [ ] Weave tracing on all LLM and tool calls
- [ ] Frozen golden set for that study
- [ ] Aria writes one new rule and one new skill per iteration
- [ ] Marimo shell: chatbot + placeholder chart + lead list

**V1 — teeth (this diagram)**
- [ ] Duplicate-lead detector as a first-class tool
- [ ] Statistical sanity tool (effect size, multiple-testing, leakage checks)
- [ ] Aria gold comparison with explicit precision / recall target
- [ ] Kit validation tests before promotion
- [ ] Rollback if gold agreement collapses
- [ ] Marimo cockpit wired to live ledger + Weave urls

**V2 — science, not demo**
- [ ] Domain packs (more OSDR missions, then materials / astro) as swappable kits
- [ ] Human escalate queue from Marimo
- [ ] Longitudinal falsification: survivors that die later punish the skill that minted them

---

A loop diagram (every round / what ships) is in `docs/helix-flow-pitch.html`; open it in a browser.

## Results so far (12-13 Sep 2026)

Two kinds of test, because they catch different mistakes. Both are judged by the same critic with the same rules file.

**LLM leads with jury labels.** The scout writes leads from the table summary, with an explicit instruction to include borderline ones. An independent two-model jury plus adjudicator labels each lead with one of seven reason codes (`scripts/jury_labels.py`). Of the 30 bad labels that have a numeric definition, 26 match the table mechanically. This set is the production distribution: messy, all six kill reasons present. 90 leads train the rules, 90 unseen leads are the holdout.

**Published NASA claims.** Claims transcribed by hand from a study's primary paper (`scripts/make_nasa_golden.py`), then checked against GeneLab's reprocessed table. A paper claim the table supports must pass; one the table does not reproduce must be killed with a stated reason. OSD-255 (retina, Mao 2019): 12 of 32 named genes reproduce at padj < 0.05 in GeneLab, direction agrees for 495 of the authors' 498 DEGs. OSD-467 (bone, Chowdhury 2021): only Pfkfb3 reproduces; 13 named genes agree in direction but not significance. This set proves the critic does not kill real biology. It cannot teach the six reason codes, because a paper never contains a merged gene symbol or a restated median.

| Set | Rules v0 | Rules v2 (ships) | Rules v4 (best on train) |
| :--- | :--- | :--- | :--- |
| LLM holdout, 90 unseen leads | reason acc 0.60, 6 false kills, 20 missed | reason acc 0.73, 8 false kills, 8 missed | reason acc 0.64, 15 false kills, 8 missed |
| OSD-255 paper, 34 claims | 0 false kills, 12 wrong reasons | 0 false kills, 4 wrong reasons | 0 false kills, 2 wrong reasons |
| OSD-467 paper, 20 claims (blind) | 0 false kills, 8 wrong reasons | 0 false kills, 3 wrong reasons | 0 false kills, 3 wrong reasons |

**Rediscovery.** Working only from the code-made table summary, the scout independently proposed each paper's headline genes, Drd4, Hist1h2bc and Sag for the retina study and Pfkfb3 for the bone study, and the critic passed those leads. It also proposed Stfa1, which the bone paper reports as differentially expressed but GeneLab's table does not reproduce (padj 0.23); the critic killed every Stfa1 lead as contradicted, citing that number.

Every remaining paper-set miss is a kill with a different reason (underpowered instead of contradicted on a padj of 0.051). No supported published finding is killed by any version.

**Why v2 ships, not v4.** The loop promotes by train score: v2 scored 0.81 there, v4 0.84. On the unseen holdout the order flips: v2 0.73, v4 0.64, and v4 kills seven more good leads for no extra junk caught. That is the training set starting to be memorised (v3 was a no-op copy of v2, and the v4 patch fixed train misses that do not generalise). `helix/product.py` therefore selects the shipped rules by holdout score, and the W&B Evals tab shows the curve v0, v1, v2, v4 on all three sets. v5 to v8 are byte-identical copies of v4 written by three later tournament rounds that found nothing better; they are not evaluated separately because they are not different rules.

**Two things the paper sets taught us.**
- *The critic will not tolerate a quoted statistic that differs from the table.* When claims carried the paper's own padj, v4 killed 5 of 15 supported claims as "contradicted", even though direction and significance agreed. A hand-written rule saying "a differing quoted number is not a contradiction" was ignored twice by the critic model. With numbers stripped, 12 of 12 pass. Training uses the number-free form; `nasa_OSD-255_numbered.json` and `results/nasa_OSD-255_numbered_rules_v*.json` keep the evidence.
- *Training on paper claims alone would be a trap.* If every "ok" came from a paper and every kill from the scout, the architect would learn to read the source, not the table. So the mixed train set (`data/golden/train.json`, 124 leads) keeps both sources inside each label: 44 ok / 46 bad from the scout, 15 ok / 19 bad from OSD-255. The LLM-only set is kept as `train_llm_only.json`. On the mixed set v4 scores 0.86 and three tournament rounds (iterations 5-7) found no candidate that beat it, so `rules_v5..v8` are unchanged copies. OSD-467 was never trained on.

---

## Quick start

```bash
# coming online during the hackathon
git clone https://github.com/<you>/helix.git
cd helix
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export WANDB_API_KEY=...
export SCOUT_MODEL=...
export CRITIC_MODEL=...   # different model. this is the whole point.
export ARIA_MODEL=...

python loop.py --data ./data/osdr_shard_01 --gold ./gold/osdr_shard_01.jsonl --iterations 3
marimo run ui/app.py
```

Open the Weave project and the Marimo app. You should see three traces, a ledger file, a gold-agreement curve, and a `kit/` diff between iteration 1 and 3.

---

## Design principles

1. **Generation and judgment never share a brain.**
2. **No lead without a DE row and a Weave trace.**
3. **Aria edits instruments, not conclusions.**
4. **Aria is scored against gold, not vibes.**
5. **Killed leads are assets.** They teach the next kit.
6. **Cheap iterations beat clever prompts.**
7. **Rollback is a feature.** Evolution without memory is drift.
8. **If a judge cannot see it in Marimo, it did not happen.**

---

## Stack

```
| Layer                      | Choice                                        |
| :------------------------- | :-------------------------------------------- |
| Source data                | NASA OSDR studies + companion papers          |
| Contrast                   | Python DGE isolation (`prep/dge.py`)          |
| Scout traces + evals       | [W&B Weave](https://wandb.ai/site/weave/)     |
| Scout / critic / architect | Separate LLMs (swap freely)                   |
| Kit format                 | Versioned rules + skills + tools on disk      |
| Orchestration              | Thin Python loop (`loop.py`)                  |
| Ledger                     | JSONL / structured store, one object per lead |
| Scoreboard                 | Frozen golden lead set per shard              |
| Interface                  | [Marimo](https://marimo.io)                   |
```

Models are interchangeable. The architecture is not.

---

## License

MIT. Science wants forks.

---

<p align="center">
<sub>Built for a hackathon. Aimed at a loop that outlives the weekend.</sub><br/>
<sub>Scout the flight data. Kill the slop. Beat the gold set. Do it again.</sub>
</p>
