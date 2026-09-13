# Helix

**A self-improving multi-agent loop that combs scientific data, finds leads, kills the bad ones, and rewrites its own playbook every iteration.**

<p align="center">
  <img src="https://img.shields.io/badge/status-hackathon-ff6b35?style=for-the-badge" alt="hackathon" />
  <img src="https://img.shields.io/badge/loop-self--evolving-7c5cff?style=for-the-badge" alt="self-evolving" />
  <img src="https://img.shields.io/badge/domain-scientific%20discovery-00c2a8?style=for-the-badge" alt="science" />
  <img src="https://img.shields.io/badge/observability-W%26B%20Weave-ffbe0b?style=for-the-badge" alt="weave" />
</p>

<p align="center">
  <strong>Scout → Critique → Evolve → Repeat</strong><br/>
  <em>Leads that survive the critic get promoted. Skills that fail get rewritten by Aria.</em>
</p>

**One sentence.** LLM agents drift, and you usually find out from a disappointed human. Helix scores every rewrite of its own rulebook on data it never trained on, and that is how it caught a rewrite that looked better and was worse, before it shipped.

## Why this exists

Scientific data is dense, noisy, and full of almost-signals. Humans miss leads because they cannot read every paper, table, spectrum, and assay at once. Naive LLM agents invent leads because nothing is allowed to say **no**.

Helix is a closed loop with three jobs that should never live in the same model:

| Role | Agent | Job |
| :--- | :--- | :--- |
| **Scout** | **Weave** | Read data. Propose leads. Emit telemetry for every claim. |
| **Critic** | Separate LLM | Shut down weak leads. Demand evidence. Score survival. |
| **Architect** | **Aria** | After each iteration, evaluate the *loop itself* and mint new rules, skills, and tools for Weave. |

The point is not “an agent that finds hypotheses.” The point is an agent that **gets better at finding hypotheses** because the loop is observable, adversarial, and allowed to rewrite its own instruments.

Yes — this is plausible. The hard parts are discipline, not magic: keep generation and judgment in different models, log everything, and let a third agent mutate the toolkit instead of the raw prompt.

---

## The loop

```text
                    ┌─────────────────────────────────────────┐
                    │              iteration n                 │
                    │                                         │
   scientific       │   ┌──────────┐      candidate leads     │
   data ───────────►│   │  WEAVE   │──────────────────┐       │
   papers, tables,  │   │  scout   │                  │       │
   assays, traces   │   │ + tools  │                  ▼       │
                    │   └────▲─────┘            ┌──────────┐  │
                    │        │                  │  CRITIC  │  │
                    │        │                  │  veto /  │  │
                    │   new rules               │  survive │  │
                    │   skills                  └────┬─────┘  │
                    │   tools                        │        │
                    │        │                       ▼        │
                    │   ┌────┴─────┐          scored ledger   │
                    │   │   ARIA   │◄──── telemetry + evals   │
                    │   │  evolve  │                          │
                    │   └──────────┘                          │
                    └──────────────────────┬──────────────────┘
                                           │
                                           ▼
                                    iteration n+1
                                    Weave runs with
                                    a different kit
```

1. **Weave** ingest scientific sources, proposes leads, and writes a full trace (inputs, tools, citations, confidence, cost).
2. **Critic** never generates. It only rejects, demotes, or conditionally promotes. Survival requires evidence, novelty, and a testable next step.
3. **Aria** does not hunt papers. It hunts *failure modes in the loop*: which skills wasted tokens, which tools hallucinated schema, which rules let junk through. Then it ships a patch — new rules, skills, tools — into Weave’s next kit.

Every cycle should leave behind a tighter scout, not just a longer list of ideas.

---

## Agents in detail

### Weave — scout + telemetry

Weave is the working scientist and the black box that is no longer a black box.

- Reads corpora, datasets, figures-as-text, and structured records.
- Proposes **leads**: short, cited, falsifiable claims with a suggested follow-up.
- Runs domain tools (retrievers, stats, plot readers, knowledge-graph hops).
- Logs every step into W&B Weave: sessions, turns, tool calls, tokens, latency, cost, and lead objects as first-class artifacts.

A lead that cannot be traced is not a lead. It is a vibe.

```text
Lead
├── claim
├── evidence[]          # paper / table / figure / row ids
├── confidence
├── novelty vs prior ledger
├── suggested experiment or analysis
└── weave_trace_id      # mandatory
```

### Critic — the shutdown valve

A different model, different prompt, different incentives.

The critic is paid to be unimpressed.

| Verdict | Meaning |
| :--- | :--- |
| **Kill** | Unsupported, circular, already known, or untestable. |
| **Park** | Interesting but under-evidenced. Do not promote. |
| **Survive** | Cited, novel enough, and has a cheap next measurement. |
| **Escalate** | High-value; needs a human or a heavier tool next round. |

Typical kill reasons the critic is required to name:

- claim does not follow from the cited rows
- lead restates a textbook result as a discovery
- no operational next step
- tool output was treated as ground truth without a sanity check
- same lead already died last iteration

Survivors go on the **ledger**. Everything else is still logged — failures are training data for Aria.

### Aria — loop architect

Aria evaluates the *system*, not the science.

After each iteration it reads:

- Weave traces and cost curves
- critic verdicts and disagreement cases
- which tools were called, which returned garbage
- which rules the scout ignored
- lead yield: proposed vs survived vs later falsified

Then it writes a patch set:

| Artifact | What Aria may mint |
| :--- | :--- |
| **Rules** | Hard constraints Weave must obey next round (“never propose a lead without a primary table id”). |
| **Skills** | Playbooks for recurring jobs (“read an RNA-seq contrast and extract only statistically backed leads”). |
| **Tools** | New or revised functions the scout can call (schema validators, duplicate-lead detectors, cheap statistical screens). |

Aria’s output is versioned. If a patch drops survival quality, roll it back. The loop is allowed to evolve; it is not allowed to forget what used to work.

---

## Why the three-way split

```text
same model  →  eloquent nonsense survives
split models →  eloquence is not evidence
```

| Coupling | Failure mode |
| :--- | :--- |
| Scout + critic in one LLM | Self-justifying leads |
| No telemetry | You cannot tell *why* a lead appeared |
| No Aria | The prompt rots; the same mistakes replay forever |
| Aria edits science instead of tools | The architect starts hallucinating biology |

Helix keeps generation, judgment, and meta-improvement on separate seats. Weave is instrumented so Aria has receipts, not vibes.

---

## What a lead is

Not a paragraph. A structured object that can die cleanly.

```json
{
  "id": "lead_0841",
  "iteration": 7,
  "claim": "Gene X upregulation co-occurs with pathway Y only in cohort Z under treatment T.",
  "evidence": [
    {"source": "GEO:GSEXXXX", "artifact": "table_de_results", "rows": ["X"]},
    {"source": "pmid:12345678", "quote_span": "…"}
  ],
  "why_not_known": "Prior reviews cover Y in general, not the T × Z interaction.",
  "next_step": "Recompute the contrast with batch covariate B; check if X remains at q < 0.05.",
  "critic": {"verdict": "survive", "score": 0.74},
  "trace": "weave://project/helix/call/..."
}
```

The ledger is the product. Papers, dashboards, and follow-up experiments are downstream of a ledger that has already been attacked.

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
│   ├── weave_scout/        # retrieval, tool use, lead writer
│   ├── critic/             # verdict-only judge
│   └── aria/               # trace miner + patch writer
├── kit/                    # living toolkit Aria mutates
│   ├── rules/
│   ├── skills/
│   └── tools/
├── ledger/                 # surviving + killed leads
├── traces/                 # W&B Weave project
└── loop.py                 # one iteration = scout → critic → aria → swap kit
```

**One training iteration** (`python3 loop.py`)

1. Load current `kit/` (rules, skills, tools).
2. Run Weave over a data shard. Emit leads + traces.
3. Run Critic over each lead. Write verdicts to the ledger.
4. Run Aria over traces + verdicts. Propose a kit diff.
5. Validate the diff (schema, tests, rollback plan).
6. Promote the new kit. Bump iteration.

Keep iteration cheap. A loop that cannot finish in minutes will not get enough generations to evolve.

---

## Results (12–13 Sep 2026)

Two kinds of test. Same critic, same rules file.

- every scout tool call is a span
- every lead is an object with a parent trace
- every critic verdict is feedback on that object
- every Aria patch is a versioned artifact tied to the iteration that produced it

**Published NASA claims.** Claims transcribed from each study's primary paper (`scripts/make_nasa_golden.py`), then checked against GeneLab's reprocessed table. A paper claim the table supports must pass; one the table does not reproduce must be killed with a stated reason.

- OSD-255 (retina, Mao 2019): 12 of 32 named genes reproduce at padj < 0.05.
- OSD-467 (bone, Chowdhury 2021): only Pfkfb3 reproduces; 13 named genes agree in direction but not significance. Never used in training.

---

## Plausibility notes

What is already real:

- Multi-agent scientific workflows that separate literature, analysis, and review
- Trace-first agent stacks (W&B Weave sessions, turns, tools, evals)
- Skill files and tool registries that an agent can rewrite between runs
- Adversarial judges that raise precision on generated hypotheses

What this project has to prove in a hackathon window:

- A lead schema strict enough to kill slop automatically
- A critic that does not rubber-stamp the scout
- An Aria step that emits *executable* kit changes, not advice
- At least one visible improvement across iterations (higher survive-rate at equal or lower cost, or fewer duplicate kills)

What we are not claiming:

- Autonomous discovery of a Nature paper by Sunday
- Replacing wet lab, statisticians, or domain review
- That Aria should have write access to production data

---

## Success criteria

A demo is winning if judges can watch **three iterations** and see the system change its own behavior.

| Signal | Good | Bad |
| :--- | :--- | :--- |
| Yield | Fewer proposals, more survivors | More proposals, same junk |
| Critic | Named kill reasons, stable rubric | “Looks good” / “not sure” |
| Aria | Diff in `kit/` that Weave actually loads | A paragraph of suggestions |
| Telemetry | Every lead has a trace id | Screenshots of a chat |
| Safety | Kit changes are reviewed / test-gated | Silent prompt injection into the scout |

---

## Roadmap

**V0 — weekend spine**
- [ ] Lead schema + ledger
- [ ] Weave scout on one corpus (papers + one tabular dataset)
- [ ] Critic with kill / park / survive
- [ ] Weave tracing on all LLM and tool calls
- [ ] Aria writes one new rule and one new skill per iteration

**V1 — teeth**
- [ ] Duplicate-lead detector as a first-class tool
- [ ] Statistical sanity tool (effect size, multiple-testing, leakage checks)
- [ ] Kit validation tests before promotion
- [ ] Rollback if survive-rate collapses

**V2 — science, not demo**
- [ ] Domain packs (bio / materials / astro) as swappable kits
- [ ] Human escalate queue
- [ ] Longitudinal falsification: survivors that die later punish the skill that minted them

---

A full-flow diagram is in `docs/helix-flow.html` and the per-version charts (train vs unseen score, mistakes by kind) in `docs/helix-charts.html`; both also render in the dashboard.

## Results so far (12-13 Sep 2026)

Two kinds of test, because they catch different mistakes. Both are judged by the same critic with the same rules file.

**LLM leads with jury labels.** The scout writes leads from the table summary, with an explicit instruction to include borderline ones. An independent two-model jury plus adjudicator labels each lead with one of seven reason codes (`scripts/jury_labels.py`). Of the 30 bad labels that have a numeric definition, 26 match the table mechanically. This set is the production distribution: messy, all six kill reasons present. 90 leads train the rules, 90 unseen leads are the holdout.

**Published NASA claims.** Claims transcribed by hand from a study's primary paper (`scripts/make_nasa_golden.py`), then checked against GeneLab's reprocessed table. A paper claim the table supports must pass; one the table does not reproduce must be killed with a stated reason. OSD-255 (retina, Mao 2019): 12 of 32 named genes reproduce at padj < 0.05 in GeneLab, direction agrees for 495 of the authors' 498 DEGs. OSD-467 (bone, Chowdhury 2021): only Pfkfb3 reproduces; 13 named genes agree in direction but not significance. This set proves the critic does not kill real biology. It cannot teach the six reason codes, because a paper never contains a merged gene symbol or a restated median.

| Set | Rules v0 | Rules v2 (ships) | Rules v4 (best on train) |
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

python loop.py --data ./data/shard_01 --iterations 3
```

Open the Weave project. You should see three traces, a ledger file, and a `kit/` diff between iteration 1 and 3.

---

## Design principles

1. **Generation and judgment never share a brain.**
2. **No lead without a trace.**
3. **Aria edits instruments, not conclusions.**
4. **Killed leads are assets.** They teach the next kit.
5. **Cheap iterations beat clever prompts.**
6. **Rollback is a feature.** Evolution without memory is drift.

---

## What we are not claiming

| Layer | Choice |
| :--- | :--- |
| Scout traces + evals | [W&B Weave](https://wandb.ai/site/weave/) |
| Scout / critic / architect | Separate LLMs (swap freely) |
| Kit format | Versioned rules + skills + tools on disk |
| Orchestration | Thin Python loop (`loop.py`) |
| Ledger | JSONL / structured store, one object per lead |

Models are interchangeable. The architecture is not.

---

## License

MIT. Science wants forks.

---

<p align="center">
  <sub>Built for a hackathon. Aimed at a loop that outlives the weekend.</sub>
</p>


## Optional TypeSafe verification and research graph

The core presentation is `app/deck.py`; its eighth tab adds saved TypeSafe results without making API calls.
Run it with `marimo run app/deck.py -p 2721`. Regenerate the static notebook with
`python3 scripts/build_deck_site.py`, then run `marimo export html-wasm deck_site.py -o ../site --mode run`
from `app/` so the stylesheet is included.

`app/lead_lab.py` adds verification of surviving leads against comparable OSDR studies.
`app/graph_lab.py` explores saved relationships among findings, paper passages, and datasets.
Both can display saved results; set `TYPESAFE_API_KEY` in `.env` to run new TypeSafe checks.
Install dependencies from `requirements.txt`. To rebuild the graph, run
`python3 -m helix.graph.build --no-explain`; this calls TypeSafe and may fetch missing corpus data.
TypeSafe verification supplements the critic's decisions and does not replace the holdout evaluation.
