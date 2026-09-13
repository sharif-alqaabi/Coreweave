# Helix: submission and 3-minute demo (13 Sep 2026)

Prize rules that apply to us: repo public, built here (47 commits, all dated 12-13 Sep, visible in git log),
W&B used (Weave, Inference, Runs, Automations), whole team present for both rounds. 3 minutes, strictly
enforced, demo-heavy, at most two slides. Judges score: Best Loop, Creativity (agents working together),
Utility, Technical execution, Sponsor usage. Plus "Most Production-Ready" two weeks later.

## What sets it apart (say at least three of these out loud)

1. **The model never touches a number.** Code attaches padj, fold change and carriers to every lead;
   the critic judges against them and cites one in every verdict.
2. **Every version is scored on data the loop never saw.** Not just "it iterates": each rulebook gets
   one look at 90 unseen leads, and that is what decides what ships.
3. **The check caught a real regression.** v4 was the best score ever on training data and worse on the
   holdout. It named training leads by id. It did not ship. That is the demo.
4. **Ground truth from outside the LLM.** 54 claims from published NASA papers: zero real findings
   killed, every unsupported claim killed with a reason.
5. **The scout rediscovers what the scientists published.** Given only the table, it proposed each
   paper's headline gene on its own: Drd4 (retina, circadian), Hist1h2bc (retina, aging), Sag (retinitis
   pigmentosa), Pfkfb3 (bone, glycolysis), and the critic passed every one. It also proposed Stfa1, which
   the bone paper reported but GeneLab's table does not reproduce, and the critic killed it citing padj 0.23.
6. **Sponsor tools are the argument, not a checkbox.** The Weave Evals page is where the catch is
   visible; each rulebook is a W&B artifact; ARIA is a contestant whose patch is in the repo.

## The one sentence

**LLM agents drift, and you usually find out from a disappointed human. Helix scores every rewrite of its
own rulebook on data it never trained on, and that is how it caught a rewrite that looked better and was
worse, before it shipped.**

---

## Submission form (AGI House platform, opens 10:00, due 13:00)

**Team name:** Helix

**Team members:** [all names, every member signed in and survey done]

**Socials:** [X / LinkedIn handles]

**Summary (2-3 sentences).**
Helix turns any of NASA's 243 spaceflight gene-expression tables into research leads a scientist can act
on, and every lead is judged against the real numbers by a critic whose rulebook rewrites itself from its
own mistakes. Three architects (Qwen, DeepSeek and ARIA) compete each round to improve the rulebook, and
every version is then scored on 90 leads the loop never saw and on 54 findings from published NASA papers.
That check caught a rewrite that scored best on training data and worse on unseen data, so it never
shipped: a self-improving loop that can also say no to itself.

**What it does / who it is for.**
A space-biology scientist uploads a NASA differential-expression table and gets, in about 100 seconds,
the hypotheses worth their time and the rejected ones with the exact number that killed each. Three
things make it trustworthy. The numbers are attached by code, so the model can never invent one. The
critic's rules were learned across three tissues and chosen by score on unseen leads, not by recency.
And the rules were validated against 54 claims from two published NASA papers: zero published findings
killed by any version, every unsupported claim killed with the number that decided it. On the way we
found that GeneLab's reprocessing does not reproduce 13 of the bone paper's confirmed genes, which is the
kind of thing this tool exists to surface.

**How it is built.**
Python. Three roles, never the same prompt: scout (proposes), critic (judges one lead against the real
table numbers and a plain-text rulebook), architects (rewrite the rulebook from the misses). Numbers are
attached to every lead by pandas, never by a model. Rulebooks are Markdown files with meta sidecars,
promoted by a tournament and gated by a holdout set. Two marimo apps: Lead Lab (product) and a
training dashboard with red/green diffs of every rulebook version. An MCP server exposes the loop's
tools (get_misses, get_rules, propose/apply patch) so ARIA can act as an architect; a W&B Automation
fires ARIA when an iteration's evaluation completes. No RL environment, no A2A.

**Sponsor tools, and how each was used.**
- **W&B Inference:** every model call in the project (scout, critic, both model architects, the label
  jury) goes through api.inference.wandb.ai. Models: Qwen3-235B, DeepSeek-V3.1, gpt-oss-120b, Kimi-K2.
- **W&B Weave:** every scout, critic and architect call is a traced op (14,380 calls, 5,845 critic
  verdicts). Every labelled lead set is a Weave Dataset; every rules version × set is a Weave Evaluation
  with two scorers, so the Evals tab compares v0/v1/v2/v4 per lead.
- **W&B Runs and Artifacts:** one run per training iteration with screening metrics and a per-lead table;
  each rulebook version is a versioned artifact with lineage to the version it consumed.
- **W&B Automations + ARIA:** an OnRunMetric automation fires SendPromptToAria when an iteration logs
  eval_complete; ARIA's patch is read back off the run and enters the tournament as a candidate. ARIA
  authored rules_v4.
- **marimo:** Lead Lab (upload a CSV, run the pipeline, read survivors and kills) and the training
  dashboard (iteration metrics, misses, rulebook diffs).

**Demo link:** repo README "Quick start"; `marimo run app/lead_lab.py`. Screen recording attached.

---

## Slide (one, the diagram)

`docs/helix-flow.html`, screenshot. Three bands: once, every round, what ships. Leave it up for the
first 40 seconds, then go to the live screens. No second slide.

---

## 3-minute script. Simple version. Say this one.

Three ideas, in this order: it proposes and checks against real numbers; it rewrites its own rules from
its mistakes; it tests every rewrite on data it never saw, and that caught a bad one. Nothing else.

**0:00 · Slide up · 25 s**
"NASA has 243 gene-expression studies from mice that flew in space. Too many for any scientist to read.
An LLM will read them, and invent findings, because nothing tells it no. Helix is an agent that tells
itself no, and gets better at it."

**0:25 · Slide, point at the middle band · 40 s**
"Three steps. One: a model reads a table and proposes leads. We didn't teach it what a good lead is. We
let it propose, and let the numbers sort. Two: code attaches the real numbers, and a separate critic kills
any lead the numbers don't support, and says why. About half survive; that's the honest ratio for an LLM
reading data. Three: the critic's rulebook is plain text, and after every round, architects rewrite it
from the critic's mistakes. That's the loop. Propose, judge, rewrite the rules, repeat."

**1:00 · Tab 1, Lead Lab, run already finished · 30 s**
"Here's a real table from a retina study. Fifty leads survive. Ten killed." Read one kill. "Every kill
cites a number from the data. The model never gets to make numbers up. And this gene here, Drd4, is the
headline finding of the published paper. The scout found it from the table alone. Never saw the paper."

**1:30 · Tab 2, Weave Evals, four holdout rows in Compare · 50 s. The pitch.**
"Now the part that matters. Four versions of the rulebook. We score each one on 90 leads it never
trained on. Version zero lets 20 bad leads through. Versions one and two catch more. Version four
scored best on the training data. On the unseen data, it's worse: it kills seven more good leads for
nothing. It had memorised the training set. This page caught it. It didn't ship. We ship version two."

**2:20 · Tab 3, dashboard, v4 diff · 20 s**
"Here's the rewrite that failed. Two lines out, one in, and the new line names training leads by id.
Every version is a W&B artifact. Every verdict, 5,800 of them, is a Weave trace. This is all live."

**2:40 · Close · 20 s**
"Agents drift. Usually a person notices, after trusting it. Here the loop noticed first, on data nobody
tuned for, and the bad version never reached a user. That's what we built this weekend."

Words not to say in the room unless asked: jury, holdout, tournament, ARIA, padj, reason accuracy. Say
"unseen data," "the numbers," "architects," "the rulebook."

### The detailed version (for questions, not for the room)

**0:00 · Slide up · Utility, 25 s**
"NASA has 243 gene-expression studies from mice that flew in space. A scientist can't read them all. An
LLM that reads them invents findings, because nothing in the loop can say no. And when an agent quietly
gets worse, you find out from a person who trusted it. Helix is built so the loop finds out first."

**0:25 · Still the slide · Creativity, agents working together, 30 s**
Point at the middle band. "Four roles, never the same job. A scout proposes. Code attaches the real
numbers. One critic judges each lead against those numbers and a plain-text rulebook. Three architects,
Qwen, DeepSeek and ARIA, rewrite that rulebook from the critic's misses, and the rewrites fight a
tournament. The critic never writes rules. The architects never judge leads. Nobody grades their own work."

**0:55 · Tab 1, Lead Lab, run already finished · Technical execution, 30 s**
"This is the product." Point at the killed table. Read one: "mean count 15, below the threshold of 20."
Point at the padj column. "Every verdict cites a number from the table. The model never gets to make
numbers up. Fifty survive, ten killed, a hundred seconds."

**1:25 · Tab 2, Weave Evals, four holdout rows in Compare · Best Loop, 50 s. This is the pitch.**
"Four versions of the rulebook. Scored on 90 leads the loop never trained on. Version zero waves through
twenty bad leads. One and two each catch more. Version four scored best on training data, and here it
kills seven more good leads for nothing. That is overfitting, in four rounds. This page is how we caught
it. We ship version two."
Click the NASA rows. "These are claims typed from the studies' published papers. Zero published findings
killed by any version. Every unsupported claim killed, with the number."

**2:15 · Tab 3, dashboard, v4 diff tab · Best Loop + Sponsor usage, 25 s**
"Here is what version four changed. Two lines out, one in: it named five training leads by id. Memorising,
not learning. Every version is a W&B artifact, every verdict is a Weave trace, every version-by-set is an
evaluation you can open right now. 5,800 verdicts, all recorded with what the critic saw."

**2:40 · Close, no screen change, 20 s**
"Agents drift. Usually a person notices. Here the loop noticed, on data nobody tuned for, and it never
reached a user. That's what we built this weekend."

Stop talking at 3:00. If you are over at 2:15, cut the NASA rows and say the sentence instead.

---

## Two questions they will ask (2 minutes optional)

- **"Why not just ship the latest version?"** "Latest was best on training data. Version two was best on
  data it hadn't seen. We ship what's measured, not what's newest."
- **"How did you know what a good lead is?"** "We didn't teach the model good. We wrote a checklist:
  the numbers back the claim, most mice show it, there's an experiment that could prove it wrong, and it
  isn't textbook. The model proposes, the checklist decides, and about half pass. Then we checked the
  checklist against the published NASA papers: our pipeline found their headline genes on its own, and
  rejected the one their own data doesn't support."
- **"Do the leads match what NASA's scientists actually found?"** "Yes. From the table alone, the scout
  proposed the headline gene of each paper, Drd4 for the retina study and Pfkfb3 for the bone study, and
  the critic passed them. It also proposed Stfa1, which the bone paper reported but the table doesn't
  reproduce, and the critic killed it with the number."
- **"Why trust the critic?"** "Zero false kills on 54 published NASA claims, one study never trained on,
  next to holdout numbers that show it isn't a rubber stamp."
- **"The paper and GeneLab disagree on some genes, who's right?"** "We don't know and the tool doesn't
  claim to. It reports what this table shows and flags the disagreement."
- **"Same model for scout and critic?"** "Yes, budget: one provider. The separation is in the inputs.
  The critic sees the table numbers, the scout doesn't. Two models would be better and we'd do that next."
- **"How are the labels made?"** "An independent LLM jury with an expert rubric, three models separate
  from the critic; 26 of the 30 numeric labels check out mechanically against the table; the published
  paper claims are the human anchor."
- **"Production-ready?"** "The product path is one function, CSV in, judged leads out, 100 seconds, and
  the rulebook it uses is chosen by holdout score, not by recency. What's missing is a second critic model
  and human review of the labels."

---

## Screen recording, under 2 minutes (do this in the morning, one take)

Voiceover is the 2-minute speech below. Shots, in order:
1. 0:00 Diagram, full screen, 20 s.
2. 0:20 Lead Lab with a finished run: scroll survivors, then the kill table, hover one reason, 25 s.
3. 0:45 Weave Traces filtered to Critic.judge, open one call, show claim, table_facts, rules, output, 20 s.
4. 1:05 Weave Evals: four holdout rows, Compare, then the two NASA rows, 30 s.
5. 1:35 Dashboard v4 diff tab, 15 s.
6. 1:50 Back to the diagram, last line of the speech.

### 2-minute voiceover

NASA has 243 gene-expression studies from mice that flew in space. A scientist can't read them all. An LLM
that reads them invents findings, because nothing in the loop is allowed to say no. And when an agent
quietly gets worse, you usually find out from a person who trusted it. We built Helix so the loop finds
out first.

Top band. This happens once. A scout model reads three NASA tables and writes 180 leads, and we tell it
to include weak ones. Code, not a model, attaches the real numbers to every lead. A jury labels each one:
fine, or one of six reasons it's bad. Then we split them. 90 for training. 90 locked away. And
separately, 54 claims typed by hand from two published NASA papers, which never touch training at all.

Middle band. This is the loop. A critic judges the 90 training leads using a rulebook, a plain-text
checklist of reasons to say no. Code finds where it disagreed with the labels. Those misses go to three
architects, Qwen, DeepSeek, and ARIA, and each rewrites the rulebook. The critic tests all three rewrites
on the same 90 leads. The best one wins, only if it beats what we had. Four rounds. Qwen won the first,
DeepSeek the second, ARIA the fourth.

Bottom band. This is the point. Every rulebook gets one look at the 90 leads it never saw. Mistakes
fell: 27, 21, 18. Then version four, ARIA's, the best score we ever got on training data, went back up
to 23. It had learned the training leads by name. On the 54 published claims, every version killed zero
real findings.

So we ship version two. Not the newest. The one that was measured. An agent drifted, the loop caught it
on data nobody tuned for, and it never reached a user. Everything you just saw is traced in Weave:
5,800 verdicts, every rulebook a versioned artifact, every version scored as an evaluation you can open
right now.

---

## Numbers to know cold

| | v0 | v1 | v2 (ships) | v4 (ARIA, caught) |
| :--- | :--- | :--- | :--- | :--- |
| Holdout false kills | 7 | 8 | 10 | 15 |
| Holdout missed kills | 20 | 13 | 8 | 8 |
| Holdout total mistakes | 27 | 21 | 18 | 23 |
| Train reason accuracy | 0.67 | 0.74 | 0.81 | 0.84 |
| NASA false kills, 54 claims | 0 | 0 | 0 | 0 |

180 leads, 90 train, 90 holdout, 54 paper claims, 4 distinct rulebooks in 8 versions, 5,845 verdicts,
14,380 traced calls, ~100 s and ~60 critic calls per Lead Lab run.

---

## What is on each screen

**Lead Lab (localhost:2719).** Survivors: lead id, shape, claim, why new (the scout's argument it isn't
already known), next step, padj (smallest adjusted p-value among cited genes; under 0.05 is
significant; blank for pathway claims), critic reason. Killed: reason code (one of six), claim, critic
reason, padj. Accordion: the summary the scout read, the rules the critic applied.

**Traces (Weave, filter All Ops to Critic.judge).** One row per verdict: claim, why_not_known, next_step,
table_facts, dataset header, sample_flags, rules text; output label, confidence, reason. Rows named
"holdout rules_v2" etc. are evaluations; their children are the same verdicts made during scoring.

**Evals (Weave).** One row per rules version per set. kill_match: false_kill, kill_correct, missed_kill.
reason_match: reason code equals the label. CriticModel:vN is Weave's object version, not the rules
version; the row name carries the rules version. Compare: tick rows, one bar chart per scorer.

**Dashboard (localhost:2718).** Score per iteration, misses handed to the architects, and one tab per
distinct rulebook with a red/green diff against its predecessor and the author.

---

## Optional opener: the naive baseline (localhost:2720, `marimo run app/naive_lab.py -p 2720`)

Same scout, same table, no numbers attached, no critic. Every lead is shown as a "finding". Have it
already run before the room. Show it for 15 seconds: "This is what an LLM research assistant gives you.
Sixty findings, all confident, none checked." Then press "Now run Helix's critic on these" and let it
run in the background while you talk; come back at the end to the kill count. On the bone table it
killed 38 of 60. Only use this if the rest of the script is under 2:30; it costs about 30 seconds of
talking plus the reveal. Never run the "Generate findings" step live: the scout can take two minutes.

## Before the room

- Restart all servers: `marimo run app/lead_lab.py -p 2719`, `marimo run app/dashboard.py -p 2718`, `marimo run app/naive_lab.py -p 2720`.
- Run Lead Lab once on a CSV from `data/raw/` and leave it up. Never run live in the room.
- Traces filtered to Critic.judge, saved as a view. Evals with the four holdout rows ticked and Compare
  open; delete the N/A row. Dashboard scrolled to the v4 diff tab.
- Diagram screenshot as the one slide. README "Results so far" open as the network-failure fallback.
- Zoom installed, or share.zoom.us tested, for the final round.
- Make the repo public before submitting. Every member: signed in, survey done.
