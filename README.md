# Helix

**A self-improving multi-agent loop that turns NASA spaceflight gene-expression tables into research leads, kills the ones the numbers do not support, and rewrites its own critic rulebook every iteration.**

<p align="center">
  <img src="https://img.shields.io/badge/status-hackathon-ff6b35?style=for-the-badge" alt="hackathon" />
  <img src="https://img.shields.io/badge/loop-self--evolving-7c5cff?style=for-the-badge" alt="self-evolving" />
  <img src="https://img.shields.io/badge/domain-NASA%20OSDR-00c2a8?style=for-the-badge" alt="nasa osdr" />
  <img src="https://img.shields.io/badge/observability-W%26B%20Weave-ffbe0b?style=for-the-badge" alt="weave" />
  <img src="https://img.shields.io/badge/architect-ARIA-7c5cff?style=for-the-badge" alt="aria" />
  <img src="https://img.shields.io/badge/ui-marimo-ff4d6d?style=for-the-badge" alt="marimo" />
  <img src="https://img.shields.io/badge/verdicts-TypeLock-00c2a8?style=for-the-badge" alt="typelock" />
</p>

<p align="center">
  <strong>Scout → Critique → Evolve → Repeat</strong><br/>
  <em>Leads that survive the critic get promoted. Rules that overfit get refused.</em>
</p>

**One sentence.** LLM agents drift, and you usually find out from a disappointed human. Helix scores every rewrite of its own rulebook on data it never trained on, and that is how it caught a rewrite that looked better and was worse, before it shipped.

Repo: [github.com/sharif-alqaabi/Coreweave](https://github.com/sharif-alqaabi/Coreweave/tree/golden-set) · branch `golden-set` · built 12–13 Sep 2026 at CoreWeave Hacks.

---

## Hackathon submission

Built this weekend. Public repo. W&B is required and used for real work, not a two-line import. No pre-hackathon product being extended; git history is the weekend.

| Field | Value |
| :--- | :--- |
| **Team name** | Helix |
| **Tracks** | Best Loop Design (all projects). Also: Best Use of Weave, Best Use of ARIA, Best Use of marimo, Best Use of TypeSafe AI. |
| **Who it is for** | A space-biology scientist staring at any of NASA OSDR's 243 differential-expression tables. |
| **Live demo** | `marimo run app/lead_lab.py` (product). `marimo run app/dashboard.py` (training diffs). `python3 loop.py --holdout --compare` (v0 vs shipped rules on 90 unseen leads). |
| **Orchestration** | Thin Python loop (`loop.py`) + MCP server (`helix/mcp_server.py`) so ARIA can act as an architect. |
| **Frameworks** | Python 3.11+, pydantic, pandas, W&B / Weave, marimo, MCP, TypeSafe TypeLock. |

### 2–3 sentence summary

Helix turns a NASA GeneLab differential-expression CSV into research leads a scientist can act on, and every lead is judged against the real table numbers by a critic whose rulebook rewrites itself from its own mistakes. Three architects (Qwen, DeepSeek, and ARIA) compete each round to improve that rulebook. Every version is then scored on 90 leads the loop never saw and on 54 findings from published NASA papers — a check that caught a rewrite which scored best on training data and worse on unseen data, so it never shipped.

---

## What it does

Upload a NASA OSDR `*_differential_expression*.csv`. In about 90–100 seconds the pipeline:

1. **Summarizes** the table in code (pandas), not in a model.
2. **Proposes** ~60 short, falsifiable leads (scout LLM).
3. **Attaches the real numbers** (padj, fold change, carriers) to every lead in code. The model never invents a statistic.
4. **Judges** each lead against those numbers and a plain-text rulebook. The verdict is a TypeLock Choice: one typed label plus a confidence.
5. **Shows** survivors and kills in Lead Lab.

Three things make that trustworthy:

- Numbers are attached by code, so the model cannot invent one.
- The critic's rules were learned across three tissues and **chosen by score on unseen leads**, not by recency.
- The same rules were checked against 54 claims from two published NASA papers: **zero supported published findings killed** by any version; every unsupported claim killed with the number that decided it.

On the way the loop surfaced that GeneLab's reprocessing does not reproduce 13 of the bone paper's confirmed genes. That is the kind of thing this tool exists to find.

---

## The loop

Generation, judgment, and meta-improvement never share a prompt.

```text
 NASA OSDR CSV
        |
        v
 +------------+   candidate leads + table_facts
 |   SCOUT    |----------------------------------+
 |  summarize |                                  |
 |  + propose |                                  v
 +-----^------+                           +------------+
       |                                  |   CRITIC   |
       |                                  | TypeLock   |
  new rules                               |  Choice    |
  (plain Markdown)                        +-----+------+
       |                                        |
       |                                  scored ledger
       |                                  + misses
       |   +------------------------------------+
       |   |
 +-----+---v------+
 |  ARCHITECTS    |   tournament: Qwen + DeepSeek + ARIA
 |  patch rules   |   score every candidate on TRAIN
 |  from misses   |   then gate what SHIPS on HOLDOUT
 +----------------+
        |
        v
  iteration n+1 uses the new rulebook
  (or the previous one, if the patch is worse)
```

1. **Scout** reads a code-made table summary and proposes leads. It is not allowed to be the source of truth for any number.
2. **Critic** never generates. TypeLock returns exactly one label (`ok`, `contradicted`, `underpowered`, `confound`, `already_known`, `untestable`, `no_mechanism`) and a confidence. The reason must cite a table number or a named rule.
3. **Architects** hunt failure modes in the critic, not papers. Each writes a patch of at most two rule sections. A tournament scores the patches on the training set. What ships is the version with the best **holdout** score.

| Role | Who | Job |
| :--- | :--- | :--- |
| Scout | Separate LLM (W&B Inference) | Propose leads from the table summary. |
| Critic | TypeLock Choice + `kit/critic/rules_v{n}.md` | Kill or keep. One typed label. Cite a number. |
| Architects | Qwen3-235B, DeepSeek-V3.1, **ARIA** | Rewrite the rulebook from misses. |
| Numbers | pandas (`helix/critic_payload.py`) | Attach padj / log2fc / carriers. Never an LLM. |
| Promotion | `helix/product.py` | Ship the holdout winner, not the newest file. |

---

## Why the three-way split

```text
same model   →  eloquent nonsense survives
split models →  eloquence is not evidence
holdout gate →  a better train score is not a better critic
typed verdict →  architects patch rules, not scraped prose
```

| Coupling | Failure mode |
| :--- | :--- |
| Scout + critic in one LLM | Self-justifying leads |
| Model-written statistics | Invented padj values |
| Parsed chat as a verdict | The loop cannot score or patch reliably |
| No telemetry | You cannot tell why a lead appeared |
| No architect | The same mistakes replay forever |
| Promote by recency or train score | Overfit rulebooks ship (this happened: v4) |
| Architect edits science instead of rules | The architect starts hallucinating biology |

---

## What a lead is

Not a paragraph. A structured object that can die cleanly.

```json
{
  "id": "OSD-421_lead_012",
  "shape": "gene",
  "claim": "Drd4 is upregulated in spaceflight retina.",
  "rows": ["Drd4"],
  "why_not_known": "Circadian receptor change is not the study headline.",
  "next_step": "Check whether the Drd4 padj survives a batch covariate.",
  "table_facts": {"Drd4": {"padj": 1.2e-4, "log2fc": 1.1, "carriers": "6/6"}},
  "label": "ok",
  "reason": "Drd4 padj=1.2e-4, direction matches the claim."
}
```

`table_facts` are attached by code after the scout writes the claim. The critic must trust `table_facts` over anything the scout quoted. The label is a TypeLock Choice, not a sentence the loop has to parse.

---

## Architecture (this build)

```text
.
├── loop.py                  # judge → score → log (fires ARIA) → tournament → write rules_v{n+1}
├── helix/
│   ├── product.py           # CSV in → judged leads out; ships best-holdout rules
│   ├── critic.py            # verdict-only judge (TypeLock Choice, @weave.op)
│   ├── critic_payload.py    # pandas attaches real numbers
│   ├── summarize.py         # code-made table summary for the scout
│   ├── reflect.py           # patch apply + guardrails (max 2 sections)
│   ├── evaluate.py          # reason accuracy, kill precision, false-kill rate
│   ├── wandb_log.py         # one W&B run + critic-rules artifact per iteration
│   ├── weave_eval.py        # Weave Evaluations: rules version × labelled set
│   ├── mcp_server.py        # MCP tools so ARIA can read misses and apply a patch
│   └── aria_channel.py      # read ARIA's patch back off the W&B run
├── agents/
│   ├── weave_scout/         # scout prompts
│   ├── critic/              # critic prompts
│   └── aria/                # architect prompts
├── kit/critic/              # living rulebooks: rules_v0.md … rules_v8.md + .meta.json
├── app/
│   ├── lead_lab.py          # marimo product UI
│   └── dashboard.py         # marimo training UI (metrics + red/green rule diffs)
├── data/
│   ├── raw/                 # OSD-104, OSD-255, OSD-421, OSD-467 DGE CSVs
│   └── golden/              # train / holdout / NASA paper claim sets
├── results/                 # per-iteration metrics, holdout scores, product dumps
└── scripts/                 # jury labels, NASA golden set, ARIA automation, Weave evals
```

**One training iteration** (`python3 loop.py`)

1. Judge the train set with `kit/critic/rules_v{n}.md`.
2. Score reason accuracy / kill precision / false-kill rate. Write `results/iter{n}.json` and `results/metrics.csv`.
3. Log a W&B run with those metrics and a versioned `critic-rules` artifact. Logging `screening/eval_complete=1` fires the ARIA automation.
4. Architects (Qwen, DeepSeek, and ARIA if `--wait-for-aria`) each propose a patch. Guardrails reject illegal patches.
5. Tournament: score every candidate on all train leads. Keep it only if it beats the current train score.
6. Rollback if precision collapses. The product path ignores train score and ships the holdout winner.

---

## Results (12–13 Sep 2026)

Two kinds of test. Same critic, same rules file.

**LLM leads with jury labels.** The scout writes leads from the table summary, told to include borderline ones. An independent two-model jury plus adjudicator labels each lead (`scripts/jury_labels.py`). 90 leads train the rules, 90 unseen leads are the holdout.

**Published NASA claims.** Claims transcribed from each study's primary paper (`scripts/make_nasa_golden.py`), then checked against GeneLab's reprocessed table. A paper claim the table supports must pass; one the table does not reproduce must be killed with a stated reason.

- OSD-255 (retina, Mao 2019): 12 of 32 named genes reproduce at padj < 0.05.
- OSD-467 (bone, Chowdhury 2021): only Pfkfb3 reproduces; 13 named genes agree in direction but not significance. Never used in training.

| Set | Rules v0 | Rules v2 (**ships**) | Rules v4 (best on train) |
| :--- | :--- | :--- | :--- |
| LLM holdout, 90 unseen leads | reason acc 0.60, 6 false kills, 20 missed | **0.73**, 8 false kills, 8 missed | 0.64, 15 false kills, 8 missed |
| OSD-255 paper, 34 claims | 0 false kills, 12 wrong reasons | 0 false kills, 4 wrong reasons | 0 false kills, 2 wrong reasons |
| OSD-467 paper, 20 claims (blind) | 0 false kills, 8 wrong reasons | 0 false kills, 3 wrong reasons | 0 false kills, 3 wrong reasons |

**Rediscovery.** Working only from the code-made table summary, the scout independently proposed each paper's headline genes — Drd4, Hist1h2bc, Sag (retina) and Pfkfb3 (bone) — and the critic passed them. It also proposed Stfa1, which the bone paper reports as DE but GeneLab does not reproduce (padj 0.23). The critic killed every Stfa1 lead as `contradicted`, citing that number.

No supported published finding is killed by any version.

**Why v2 ships, not v4.** The loop promotes by train score: v2 scored 0.81 there, v4 scored 0.84. On the unseen holdout the order flips: v2 0.73, v4 0.64, and v4 kills seven more good leads for no extra junk caught. v4 named training leads by id. That is memorization, so it did not ship. `helix/product.py` selects by holdout score. v5–v8 are byte-identical copies of v4 from later tournament rounds that found nothing better.

Train metrics from `results/metrics.csv`:

| iter | rules | reason acc (train) | kill precision | misses |
| ---: | ---: | ---: | ---: | ---: |
| 0 | v0 | 0.68 | 0.93 | 29 |
| 1 | v1 | 0.74 | 0.89 | 23 |
| 2 | v2 | 0.81 | 0.89 | 17 |
| 3 | v3 (= v2) | 0.81 | 0.89 | 17 |
| 4 | v4 | 0.84 | 0.85 | 14 |
| 5–7 | v5–v7 (= v4 text) | 0.86–0.87 on mixed train | 0.88 | 16–17 |

---

## Sponsor tools (how each was used)

Handbook rule: list every sponsor tool and how you used it. This is scored for sponsor prizes and grand prizes.

| Tool | How Helix uses it |
| :--- | :--- |
| **W&B Inference** | Every generative model call — scout, both model architects, label jury — goes through `api.inference.wandb.ai`. Models: Qwen3-235B-A22B-Instruct-2507, DeepSeek-V3.1, gpt-oss-120b, Kimi-K2. |
| **W&B Weave** | Every scout / critic / architect call is a traced `@weave.op` (14,380 calls, 5,845 critic verdicts in the recorded run). Each labelled lead set is a Weave Dataset. Each rules version × set is a Weave Evaluation with two scorers, so the Evals tab compares v0 / v1 / v2 / v4 per lead. |
| **W&B Runs + Artifacts** | One run per training iteration (`job_type=critic-iteration`) with `screening/*` metrics and a per-lead table. Each rulebook is a versioned `critic-rules` artifact with lineage to the version it consumed. |
| **W&B Automations + ARIA** | `scripts/create_aria_automation.py` registers `OnRunMetric(screening/eval_complete >= 1) >> SendPromptToAria`. ARIA's patch is read back off the run (`helix/aria_channel.py`) and enters the tournament as a candidate. ARIA authored `rules_v4`. |
| **MCP** | `helix/mcp_server.py` exposes `list_iterations`, `get_misses`, `get_rules`, `get_dataset_summary`, `propose_rules_patch`, `apply_rules_patch` (compare-and-swap on the rules digest). That is how ARIA acts as an architect instead of a chatbot. |
| **marimo** | `app/lead_lab.py` — upload a CSV, run the product pipeline, read survivors and kills. `app/dashboard.py` — iteration metrics and red/green diffs of every rulebook version. |
| **TypeSafe TypeLock** | The critic verdict is a TypeLock Choice, not parsed chat: one label from `{ok, contradicted, underpowered, confound, already_known, untestable, no_mechanism}` plus a confidence the loop can threshold on. Same typed decision on every lead, so architects patch rules instead of scraping prose. |

W&B project from `.env.example`: entity `matthewma003-san-jose-state-university`, project `helix`. The handbook says the project does not need to be public; still paste the link on the AGI House form.

---

## Quick start

```bash
git clone -b golden-set https://github.com/sharif-alqaabi/Coreweave.git
cd Coreweave
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set WANDB_API_KEY

# plumbing only, no keys
python3 loop.py --iterations 1 --dry-run

# product path: one NASA table → judged leads (~90 s, needs inference)
python3 -m helix.product data/raw/OSD-421_differential_expression.csv

# score shipped rules vs v0 on the 90 unseen leads
python3 loop.py --holdout --compare

# live UI
marimo run app/lead_lab.py
marimo run app/dashboard.py
```

Useful loop flags:

```bash
python3 loop.py --iterations 4 --wait-for-aria 120
python3 loop.py --judge 4 --group demo
python3 loop.py --revise 4 --wait-for-aria 30
python3 loop.py --holdout --holdout-file data/golden/nasa_OSD-467.json --compare
```

Publish Weave Evaluations (Evals tab):

```bash
python3 scripts/weave_eval.py data/golden/holdout.json 0 4
```

MCP server if ARIA (or any client) should talk to the kit directly:

```bash
python3 helix/mcp_server.py          # http://0.0.0.0:8765/mcp
```

---

## Design principles

1. **Generation and judgment never share a brain.**
2. **The model never touches a number.** pandas attaches padj / fold change / carriers.
3. **A verdict is a typed Choice, not a paragraph.** TypeLock returns one label and a confidence.
4. **No lead without a trace.** Every critic call is a Weave op.
5. **Architects edit the rulebook, not the biology.**
6. **Killed leads are assets.** They are the training data.
7. **Train score proposes. Holdout score ships.**
8. **Rollback is a feature.** Evolution without memory is drift.

---

## What we are not claiming

- Autonomous discovery of a Nature paper by Sunday.
- Replacing wet lab, statisticians, or domain review.
- That every NASA GeneLab reprocessing agrees with the original paper. It does not; Helix is useful partly because it surfaces that.

---

## License

MIT. Science wants forks.
