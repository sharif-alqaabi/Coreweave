# Helix

**A self-improving research loop. It reads a dataset, proposes findings, kills the ones the data does not support, rewrites its own critic every round, and then checks what survived against every other dataset and paper in the field.**

<p align="center">
  <img src="https://img.shields.io/badge/status-hackathon-ff6b35?style=for-the-badge" alt="hackathon" />
  <img src="https://img.shields.io/badge/loop-self--evolving-7c5cff?style=for-the-badge" alt="self-evolving" />
  <img src="https://img.shields.io/badge/domain-any%20research%20field-00c2a8?style=for-the-badge" alt="any research field" />
  <img src="https://img.shields.io/badge/observability-W%26B%20Weave-ffbe0b?style=for-the-badge" alt="weave" />
  <img src="https://img.shields.io/badge/architect-ARIA-7c5cff?style=for-the-badge" alt="aria" />
  <img src="https://img.shields.io/badge/verification-TypeSafe-6d28d9?style=for-the-badge" alt="typesafe" />
  <img src="https://img.shields.io/badge/ui-marimo-ff4d6d?style=for-the-badge" alt="marimo" />
</p>

<p align="center">
  <strong>Propose → Judge → Rewrite the rules → Repeat → Verify against the field</strong><br/>
  <em>Every rewrite must beat the old rules on data it never saw. Every survivor is checked against every other study.</em>
</p>

**One sentence.** LLM research assistants drift, and you usually find out from a disappointed human. Helix scores every rewrite of its own rulebook on data it never trained on, which is how it caught a rewrite that looked better and was worse before it shipped; then it checks every surviving finding against the rest of the field, which is how it found that 35 of 38 "novel" leads were already replicated elsewhere.

Repo: [github.com/sharif-alqaabi/Coreweave](https://github.com/sharif-alqaabi/Coreweave) · branch `main` · built 12–13 Sep 2026 at CoreWeave Hacks.

---

## What Helix is for

Any research field where a claim can be checked against a table and against the literature: transcriptomics, materials characterisation, clinical cohorts, climate reanalysis, survey data. The loop, the critic, the architects, the holdout gate, the verification and the research graph are domain-agnostic. Four things are domain adapters, listed in [Bringing Helix to another field](#bringing-helix-to-another-field).

The first field it was proven on is NASA's Open Science Data Repository: 243 differential-expression tables from spaceflight biology, each ~20,000 genes with fold changes and adjusted p-values, plus the 150 papers OSDR links to them. Everything in [Results](#results-on-the-first-field-nasa-osdr-1213-sep-2026) is measured there.

---

## Hackathon submission

Built this weekend. Public repo. W&B is used for real work, not a two-line import. No pre-hackathon product being extended; the git history is the weekend.

| Field | Value |
| :--- | :--- |
| **Team** | Helix |
| **Tracks** | Best Loop Design. Also: Best Use of Weave, Best Use of ARIA, Best Use of marimo, Best Use of TypeSafe AI. |
| **Who it is for** | A researcher staring at a data table they do not have a week to read. First user: a space-biology scientist with any of OSDR's 243 tables. |
| **Live demo** | `marimo run app/deck.py -p 2721` (the presentation, nine slides, all preloaded). `app/lead_lab.py -p 2719` (product). `app/graph_lab.py -p 2722` (research graph). `app/dashboard.py -p 2718` (training diffs). |
| **Orchestration** | Thin Python loop (`loop.py`), an MCP server (`helix/mcp_server.py`) so ARIA can act as an architect, TypeSafe for every semantic judgment after the loop. |
| **Frameworks** | Python 3.11+, pandas, pydantic, W&B Inference / Weave / Automations, marimo, MCP, TypeSafe SDK, LangGraph, Instructor, LiteLLM, DSPy, model2vec, DuckDB. |

**Summary.** Helix turns a research data table into findings a scientist can act on. Every finding is judged against the real numbers by a critic whose rulebook rewrites itself from its own mistakes; three architects (Qwen, DeepSeek, and W&B's ARIA) compete each round, and every version is scored on leads the loop never saw and on 54 findings from published papers, a check that caught an overfit rewrite before it shipped. Then TypeSafe checks every survivor against the other 242 datasets in the field and links every finding Helix has ever produced to the passages in 150 papers that support or contradict it.

---

## What it does

Upload one table. In about 90 seconds:

1. **Code summarises** the table (pandas). The model never sees raw rows.
2. **A scout LLM proposes** ~60 short, falsifiable findings: single variables, families, pathways, global patterns.
3. **Code attaches the real numbers** to every finding: effect size, adjusted p-value, how many samples carry the signal. The model never writes a statistic.
4. **A separate critic LLM judges** each finding against those numbers and a plain-text rulebook. One of seven labels: `ok`, `contradicted`, `underpowered`, `confound`, `already_known`, `untestable`, `no_mechanism`, with the number that decided it. The verdict is a validated pydantic model (Instructor re-prompts the model with the validation error on a bad reply), so nothing is scraped out of prose.
5. **Lead Lab shows** survivors and kills, and the **OSDR check**: whether each survivor replicates in any other dataset in the field.

On the OSD-421 thymus table: 38 survive, 22 killed. On the OSD-255 retina table the scout, given only the table, proposed the paper's own headline genes (Drd4, Sag, Hist1h2bc) and the critic passed them; it also proposed Stfa1, which the bone paper reports but the reprocessed table does not reproduce, and the critic killed it citing padj 0.23.

---

## The loop

Generation, judgment and meta-improvement never share a prompt.

```text
 data table
     |
     v
 +------------+   findings + real numbers (code)
 |   SCOUT    |----------------------------------+
 | summarise  |                                  |
 | + propose  |                                  v
 +-----^------+                           +------------+
       |                                  |   CRITIC   |
       |                                  | one label  |
  new rulebook                            | + a number |
  (plain Markdown)                        +-----+------+
       |                                        |
       |                                  verdicts vs labels
       |                                  -> list of misses
       |   +------------------------------------+
       |   |
 +-----+---v------+
 |  ARCHITECTS    |   Qwen + DeepSeek + ARIA each rewrite the rulebook
 |  patch rules   |   tournament: re-judge all train leads with each candidate
 |  from misses   |   best wins, only if it beats the current version
 +----------------+
        |
        v
  the promoted version is then scored on HOLDOUT leads and on PUBLISHED CLAIMS
  what ships is the best holdout score, not the newest file
```

| Role | Who | Job |
| :--- | :--- | :--- |
| Scout | Qwen3-235B via W&B Inference | Propose findings from the code-made summary. |
| Numbers | pandas (`helix/critic_payload.py`) | Attach effect, p-value, carriers to every cited variable. Never an LLM. |
| Critic | Separate LLM + `kit/critic/rules_v{n}.md` | One label per finding. Cite a number or a named rule. |
| Architects | Qwen3-235B, DeepSeek-V3.1, **ARIA** | Rewrite the rulebook from the misses. At most 3 sections per patch (`helix/reflect.py`). |
| Jury | DeepSeek, gpt-oss-120b, Kimi-K2 adjudicates | Labelled the training and holdout leads once (`scripts/jury_labels.py`). Never the critic. |
| Promotion | `helix/product.py` | Ships the version with the best holdout score. |

**As a state graph.** `python -m helix.orchestrate round --n 3 --approve` runs the same round as a checkpointed LangGraph: the architects fan out in parallel, the run resumes from its last completed node after a failure, and `--approve` pauses before promotion until a person answers (`resume --thread round-3`). The graphs are drawn from the code in [docs/orchestration.md](docs/orchestration.md).

**ARIA as an architect.** A W&B Automation fires ARIA when an iteration's evaluation lands (`scripts/create_aria_automation.py`). ARIA reads the run's misses table and the rules artifact, writes a patch onto the run (`helix/aria_channel.py` reads it back), and the patch enters the tournament as a contestant. ARIA authored `rules_v2`, the version that ships. The MCP server (`helix/mcp_server.py`: `list_iterations`, `get_misses`, `get_rules`, `get_dataset_summary`, `propose_rules_patch`, `apply_rules_patch`) is the tool surface for any MCP-capable agent to do the same.

---

## After the loop: verify against the field, then link everything

Every survivor says *why it is new*, usually "not replicated in other studies". Nobody checks. Helix does, with **TypeSafe (Jev)**, a System One model that answers with typed labels and calibrated probabilities instead of prose, in about a second per request.

**Verification (`helix/replicate.py`).** For each survivor:
- *Tier 1, the catalog.* Jev scores every same-organism dataset in the field: could this study replicate or refute the finding (0–3), and does it test the same condition? 120 studies per finding, no downloads.
- *Tier 2, the numbers.* For comparable datasets on disk, pandas tallies each variable as same / opposite / no change; Jev judges what that means given the tissue. A code gate keeps the policy explicit: an unrelated tissue is always inconclusive, `contradicted` needs a significant opposite-direction variable, `replicated` a significant same-direction one.

38 survivors against 120 studies in 15 s. The scout's novelty claim was wrong on 35 of 38: the same genes move the same way in two other spaceflight-thymus flights. Three findings are seen nowhere else, and those are the ones worth a scientist's time. The critic's verdict is never changed by this.

**Research graph (`helix/graph/`).** Every finding Helix has produced or checked (294: leads, survivors, the 54 paper claims) linked to the field's literature. Code fetches the papers the data repository links to its studies (150 papers; abstracts via PubMed, open-access full text via PMC for 140, citation counts from Semantic Scholar), cuts them into 12,152 passages, and tags entities against a vocabulary built from the tables themselves. Code proposes candidate pairs from shared entities and from a semantic index (model2vec static embeddings over every passage, built in 6 s); TypeSafe does the rest:
- *Rerank.* A pool of up to 120 passages per finding, one relevance probability each, top 30 kept. The embedding index adds passages no entity match can reach: 204 kept edges in the current build come only from it, e.g. "histone genes dominate the downregulated list" → the OSD-289 paper's *"Down-regulated genes in the MG group included many histone genes"*.
- *Type each pair.* `supports` / `contradicts` / `background` for finding→passage; `replicates` / `contradicts` / `extends` / `rediscovers` for finding→finding; each with dedicated gating probabilities so a passage that merely names the variable cannot count as a contradiction.
- ~10,000 pair judgments in 90 s. Every edge keeps its full distribution; thresholds are sliders, not reruns. A regular LLM only writes the one-sentence explanation of links already accepted.

What it found: 75 findings contradicted by a passage (44 before the semantic index), for example "Crb1 downregulated in the spaceflight retina" against the retina paper's own sentence, *"None of the disease-associated genes … were differentially expressed in spaceflight"*, the sentence the human labeller had cited. The scout's Drd4, Sag, Pfkfb3 and Stfa1 leads linked automatically to the papers' claims. And semantic, not keyword: E2f7, named in no paper, linked to a thymus paper's "reduced expression of cell cycle-regulating genes" at the pathway level. Explore it in Graph Lab.

---

## Results on the first field, NASA OSDR (12–13 Sep 2026)

Two kinds of test, because they catch different mistakes. Both are judged by the same critic with the same rules file.

**LLM leads with jury labels.** The scout writes leads from the table summary, with an explicit instruction to include borderline ones. An independent two-model jury plus adjudicator labels each lead with one of seven reason codes (`scripts/jury_labels.py`). 90 leads train the rules, 90 unseen leads are the holdout.

**Published claims.** Claims transcribed by hand from a study's primary paper (`scripts/make_nasa_golden.py`), then checked against the repository's reprocessed table. A paper claim the table supports must pass; one the table does not reproduce must be killed with a stated reason. OSD-255 (retina, Mao 2019): 12 of 32 named genes reproduce at padj < 0.05. OSD-467 (bone, Chowdhury 2021): only Pfkfb3 reproduces; the other named genes agree in direction but not significance. This set proves the critic does not kill real published findings.

| Set | Rules v0 | Rules v2 (**ships**) | Rules v4 (best on train) |
| :--- | :--- | :--- | :--- |
| LLM holdout, 90 unseen leads | reason acc 0.60, 6 false kills, 20 missed | **0.73**, 8 false kills, 8 missed | 0.64, 15 false kills, 8 missed |
| OSD-255 paper, 34 claims | 0 false kills, 12 wrong reasons | 0 false kills, 4 wrong reasons | 0 false kills, 2 wrong reasons |
| OSD-467 paper, 20 claims (blind) | 0 false kills, 8 wrong reasons | 0 false kills, 3 wrong reasons | 0 false kills, 3 wrong reasons |

**Rediscovery.** Working only from the code-made table summary, the scout independently proposed each paper's headline genes, Drd4, Hist1h2bc and Sag for the retina study and Pfkfb3 for the bone study, and the critic passed those leads. It also proposed Stfa1, which the bone paper reports as differentially expressed but the reprocessed table does not reproduce (padj 0.23); the critic killed every Stfa1 lead as `contradicted`, citing that number. No supported published finding is killed by any version.

**Why v2 ships, not v4.** The loop promotes by train score: v2 scored 0.81 there, v4 0.84. On the unseen holdout the order flips: v2 0.73, v4 0.64, and v4 kills seven more good leads for no extra junk caught. That is the training set starting to be memorised. `helix/product.py` therefore selects the shipped rules by holdout score. v3 is a byte-identical copy of v2 and v5 to v8 are copies of v4, written by tournament rounds that found nothing better.

Train metrics from `results/metrics.csv`:

| iter | rules | reason acc (train) | kill precision | misses |
| ---: | ---: | ---: | ---: | ---: |
| 0 | v0 | 0.68 | 0.93 | 29 |
| 1 | v1 | 0.74 | 0.89 | 23 |
| 2 | v2 | 0.81 | 0.89 | 17 |
| 3 | v3 (= v2) | 0.81 | 0.89 | 17 |
| 4 | v4 | 0.84 | 0.85 | 14 |
| 5–7 | v5–v7 (= v4) | 0.86–0.87 on mixed train | 0.88 | 16–17 |

**Two things the paper sets taught us.**
- *The critic will not tolerate a quoted statistic that differs from the table.* When claims carried the paper's own padj, v4 killed 5 of 15 supported claims as "contradicted" even though direction and significance agreed. With numbers stripped, 12 of 12 pass. Training uses the number-free form; `data/golden/nasa_OSD-255_numbered.json` keeps the evidence.
- *Training on paper claims alone would be a trap.* If every "ok" came from a paper and every kill from the scout, the architect would learn to read the source, not the table. The mixed train set keeps both sources inside each label. OSD-467 was never trained on.

**Verification and graph.** 38 survivors verified against 120 studies in 15 s (35 replicated elsewhere, 3 unique). Graph over 294 findings and 150 papers, hackathon build: 9,557 pairs scored in 90 s; 407 findings supported by a passage, 44 contradicted, 5 rediscoveries, 71 replicated by another dataset's numbers. Current build with the semantic index: 9,858 pairs in 117 s; 459 supported, 75 contradicted, 204 kept edges reachable only by embedding. Saved in `results/replicate_OSD-421.json` and `results/graph.json`.

**How good are TypeSafe's judgments?** `python -m helix.graph.evaluate` scores finding–passage relations against human labels in `data/golden/graph_pairs.jsonl` (precision, recall, F1 per relation, confusion matrix). The file currently holds 12 pairs from the developer's spot checks during the build, so its 0.92 accuracy is a smoke test, not a result; `--export 60` writes a stratified sample for a scientist to label, which is the number to quote.

**Is a tournament of LLM architects better than a standard prompt optimiser?** `python -m helix.dspy_baseline` runs the critic as a DSPy program, optimises it on the same train set (BootstrapFewShot or MIPROv2) and scores it on the same holdout, writing a row that sits next to rules_v0 / v2 / v4. Not yet run: it needs an inference key.

---

## Bringing Helix to another field

Everything above is domain-agnostic except four adapters. Replace these and the loop, the tournament, the holdout gate, the verification tiers and the graph run unchanged:

| Adapter | File | What it does today (OSDR) | What it needs for a new field |
| :--- | :--- | :--- | :--- |
| Summariser | `helix/summarize.py` | Turns a differential-expression CSV into a ~600-token summary: top effects, pathway enrichment, sample flags. | A function from your table to a summary the scout can propose from. |
| Numbers | `helix/critic_payload.py` | Looks up log2fc, padj, carriers, mean counts per cited gene or GO term. | A lookup from a cited variable to its real statistics. |
| Rulebook seed | `kit/critic/rules_v0.md` | Seven reason codes with numeric thresholds for gene expression. | The reason codes and thresholds of your field, in plain text. The loop rewrites them from there. |
| Corpus | `helix/graph/corpus.py`, `helix/graph/entities.py` | Study catalog → PubMed → PMC; gene symbols matched against the tables' own vocabulary; tissue and condition regexes. | Where your field's papers live, and the entity vocabulary to match. |

The critic prompt, the architects, the jury, the holdout split, `helix/replicate.py`'s two tiers and `helix/graph/edges.py`'s judgments do not mention genes.

---

## Engineering choices

| Need | Choice | Where |
| :--- | :--- | :--- |
| Typed verdicts | **Instructor** + pydantic `Verdict` (label ∈ 7 codes, confidence ∈ [0, 1]); regex parse only as the last fallback | `helix/critic.py`, `helix/llm.py` |
| Any model provider | **LiteLLM** as a fourth route beside Anthropic / W&B Inference / OpenAI-compatible; one `chat()` and one `chat_typed()` | `helix/llm.py`, `LLM_PROVIDER=litellm` |
| Configuration | **pydantic-settings**: every key and model name in one `Settings`, read from `.env`, same names as before | `helix/settings.py` |
| Orchestration | **LangGraph** state graphs with a SQLite checkpointer: product pipeline and training round; resume, fan-out, approval interrupt | `helix/orchestrate.py`, `docs/orchestration.md` |
| Semantic candidates | **model2vec** static embeddings (numpy-only, no torch): 12k passages embedded in 6 s, cosine search in numpy | `helix/graph/index.py` |
| Judgment evaluation | **scikit-learn** metrics over a human-labelled pair file | `helix/graph/evaluate.py`, `data/golden/graph_pairs.jsonl` |
| Optimiser baseline | **DSPy** (BootstrapFewShot / MIPROv2) on the same splits as the tournament | `helix/dspy_baseline.py` |
| Field-wide lookups | **DuckDB** over the CSVs in place: any gene across every table in 2.5 s | `helix/tables.py` |
| Literature | NCBI E-utilities for PubMed and PMC full text, **Semantic Scholar** for citation counts | `helix/graph/corpus.py` |
| New-field entities | **GLiNER** zero-shot NER behind `HELIX_NER=gliner` (optional, needs torch); regex vocabularies stay the default | `helix/graph/entities.py` |

Not used, on purpose: LangChain chains and agent frameworks (one `chat()` per stage, nothing to chain; the roles are deliberately not conversational agents), RAG frameworks (the rerank-then-judge design is more specific than what they offer), LangSmith (Weave already traces everything, including the LangGraph runs).

---

## Architecture

```text
.
├── loop.py                  # judge → score → log (fires ARIA) → tournament → write rules_v{n+1}
├── helix/
│   ├── product.py           # table in → judged findings out; ships the best-holdout rules
│   ├── summarize.py         # code-made table summary                          [adapter]
│   ├── critic_payload.py    # pandas attaches the real numbers                 [adapter]
│   ├── critic.py            # verdict-only judge, one label + a number, @weave.op
│   ├── reflect.py           # patch apply + guardrails (max 3 sections)
│   ├── evaluate.py          # reason accuracy, kill precision, false-kill rate
│   ├── llm.py               # one chat() / chat_typed() for every generative call; provider from .env
│   ├── settings.py          # pydantic-settings: every key and model name
│   ├── orchestrate.py       # LangGraph: product pipeline and training round, checkpointed
│   ├── dspy_baseline.py     # the critic as a DSPy program, optimised on train, scored on holdout
│   ├── tables.py            # DuckDB lookups across every table on disk
│   ├── wandb_log.py         # one W&B run + critic-rules artifact per iteration
│   ├── weave_eval.py        # Weave Evaluations: rules version × labelled set
│   ├── mcp_server.py        # MCP tools so ARIA can read misses and apply a patch
│   ├── aria_channel.py      # read ARIA's patch back off the W&B run
│   ├── replicate.py         # TypeSafe: verify every survivor against the field
│   └── graph/               # TypeSafe: corpus, entities, index (embeddings), edges, explain, build, evaluate
├── kit/critic/              # living rulebooks: rules_v0.md … rules_v8.md + .meta.json   [adapter: v0]
├── app/
│   ├── deck.py              # the presentation, nine slides, all preloaded
│   ├── lead_lab.py          # product UI + OSDR check
│   ├── graph_lab.py         # research graph explorer
│   ├── dashboard.py         # training metrics + red/green rule diffs
│   └── naive_lab.py         # the same table through an LLM with no critic
├── data/
│   ├── osdr_catalog.csv     # 243 studies
│   ├── raw/                 # DGE tables (4 tracked; more pulled on demand)
│   ├── golden/              # train / holdout / paper claim sets
│   └── corpus/              # fetched papers and passages (cached, not tracked)
├── results/                 # per-iteration metrics, holdout scores, product runs, verification, graph
├── docs/                    # flow diagrams, charts, orchestration.md (the state graphs)
├── scripts/                 # jury labels, golden sets, ARIA automation, Weave evals, deck build
└── DEMO.md                  # the three-minute script and judge Q&A
```

---

## Sponsor tools

| Tool | How Helix uses it |
| :--- | :--- |
| **W&B Inference** | Every generative call, scout, both model architects and the label jury, goes through `api.inference.wandb.ai`. Models: Qwen3-235B-A22B-Instruct-2507, DeepSeek-V3.1, gpt-oss-120b, Kimi-K2. |
| **W&B Weave** | Every scout / critic / architect call is a traced `@weave.op` (14,380 calls, 5,845 verdicts in the recorded run). Each labelled lead set is a Weave Dataset; each rules version × set is a Weave Evaluation with two scorers, so the Evals tab compares v0 / v1 / v2 / v4 per lead. |
| **W&B Runs + Artifacts** | One run per training iteration with `screening/*` metrics and a per-lead table. Each rulebook is a versioned `critic-rules` artifact with lineage to the version it consumed. |
| **W&B Automations + ARIA** | `OnRunMetric(screening/eval_complete >= 1) >> SendPromptToAria`. ARIA's patch is read back off the run and enters the tournament as a candidate. ARIA authored `rules_v2`, the version that ships. |
| **MCP** | `helix/mcp_server.py` exposes the kit to any MCP-capable agent, with compare-and-swap on the rules digest. |
| **marimo** | Four apps and the deck itself. Lead Lab, Graph Lab, the dashboard's red/green rule diffs, the naive baseline, and a nine-slide presentation exported as a static WebAssembly site. |
| **TypeSafe** | Jev, a System One model, supplies every semantic judgment after the loop: study comparability, cross-dataset replication given the tissue, passage relevance, finding–passage and finding–finding relationships, and gene-symbol disambiguation. ~10,000 judgments in 90 s, each a typed answer with its probability distribution; every threshold and gate is a readable code rule. |

---

## Quick start

```bash
git clone https://github.com/sharif-alqaabi/Coreweave.git
cd Coreweave
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # WANDB_API_KEY for the scout / critic / architects; TYPESAFE_API_KEY for verification and the graph
```

```bash
# the presentation and the apps (saved results, no keys needed)
marimo run app/deck.py -p 2721
marimo run app/lead_lab.py -p 2719
marimo run app/graph_lab.py -p 2722
marimo run app/dashboard.py -p 2718
```

```bash
# product path: one table -> judged findings (~90 s, needs WANDB_API_KEY)
python3 -m helix.product data/raw/OSD-421_differential_expression.csv

# verify the survivors against the field (~15 s, needs TYPESAFE_API_KEY)
python3 helix/replicate.py results/product_OSD-421.json

# rebuild the research graph (~90 s; first run fetches the corpus, ~5 min)
python3 -m helix.graph.build --no-explain

# score shipped rules vs v0 on the 90 unseen leads
python3 loop.py --holdout --compare

# one training round; plumbing only with --dry-run
python3 loop.py --iterations 1 --dry-run
python3 loop.py --iterations 4 --wait-for-aria 120
```

```bash
# the same, as checkpointed state graphs (resume after a failure; pause for approval before promotion)
python3 -m helix.orchestrate product data/raw/OSD-421_differential_expression.csv
python3 -m helix.orchestrate round --n 3 --wait-for-aria 120 --approve
python3 -m helix.orchestrate resume --thread round-3

# how good are the graph's judgments; export a sample for a scientist to label
python3 -m helix.graph.evaluate
python3 -m helix.graph.evaluate --export 60

# where else does a gene move, across every table on disk
python3 -m helix.tables Pfkfb3

# the DSPy baseline for the critic (needs an inference key)
python3 -m helix.dspy_baseline --optimizer bootstrap
```

---

## Design principles

1. **Generation and judgment never share a brain.**
2. **The model never writes a number.** Effect sizes, p-values, carriers, direction agreement: all code.
3. **Train score proposes. Holdout score ships.**
4. **Architects edit the rulebook, not the science.**
5. **Judgments are probabilities; verdicts are code.** TypeSafe supplies calibrated semantic judgment; every threshold is a readable rule.
6. **No finding without a trace.** Every critic call is a Weave op; every edge keeps its distribution.
7. **Killed findings are assets.** They are the training data.
8. **Rollback is a feature.** Evolution without memory is drift.

---

## What we are not claiming

- Autonomous discovery. Helix finds, checks and ranks; a scientist decides.
- Replacing wet lab, statisticians or domain review.
- That the first field is the only field. It is the one we could measure in a weekend; the adapters above are the whole cost of the next one.
- That a data repository's reprocessing agrees with the original paper. It often does not, and Helix is useful partly because it surfaces exactly that.

---

## License

MIT. Science wants forks.
