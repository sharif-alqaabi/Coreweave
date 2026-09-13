# Helix: demo script (13 Sep 2026)

## The pitch, in one breath. Say this first and say it last.

**LLMs are not deterministic, so a bad change to an agent is usually caught late, by a disappointed
human. Helix catches it in the loop. Every rewrite of the critic's rulebook is scored on leads it has
never seen and on claims from published NASA papers. One rewrite looked better on training data and
was worse on unseen data. The loop caught it, and it did not ship.**

That is the whole story. Everything on screen is evidence for one of its three claims:
1. the rules change (self-improving),
2. the change is measured on unseen data (not just on what it trained on),
3. one change overfit and was caught (the loop says no to itself).

## Submission form

**Project name:** Helix

**Description:** Helix reads a NASA OSDR gene-expression table, proposes research leads, and lets a
separate critic kill the weak ones with a stated reason. After every round an architect rewrites the
critic's rulebook from the misses, and candidate rulebooks fight a tournament before promotion. It is
self-improving because the rulebook is a versioned artifact that changes the critic's behaviour, and
every version is scored on unseen leads and on published NASA findings, so a rewrite that overfits is
caught before it ships.

**Track:** Best Use of Weave. Also eligible for Best Loop Design.

**Demo:** `marimo run app/lead_lab.py`, upload any `*_differential_expression.csv` from `data/raw/`.
The W&B Evals tab shows the trained-versus-untrained comparison with no setup.

## 3-minute script

**0:00 The problem (no screen).**
"NASA has 243 gene-expression studies from spaceflight mice. A scientist can't read them all. An LLM that
reads them invents findings, because nothing in the loop is allowed to say no. And when an agent gets
worse, you usually find out from a human who trusted it. Helix is built so the loop finds out first."

**0:30 Lead Lab (tab 1, run already finished).**
"Upload a table, the scout proposes 60 leads, code attaches the real numbers, a separate critic kills
the weak ones with a reason." Read one kill: "mean count 15, below the threshold of 20." Point at the
padj column. "Every verdict cites a number from the table. The model never gets to make numbers up."

**1:00 Traces (tab 2, filtered to Critic.judge).**
"5,800 verdicts, each one recorded with exactly what the critic saw: the claim, the numbers, the rules
text, and its answer. Nothing is a black box, which is what makes the next part possible."

**1:30 Evals (tab 3, four holdout rows selected, Compare open).**
"Four versions of the rulebook, written by three different architects from the critic's misses. Scored
on 90 leads the loop never trained on. v0 waves through 20 bad leads. v1 and v2 each catch more.
v4 scored best on training data and here it kills seven more good leads for nothing. That's overfitting,
in four rounds, and this page is how we caught it. We ship v2."
Then the NASA rows: "These are claims transcribed from the studies' published papers. Zero published
findings killed by any version, every unsupported claim killed with the number that decided it."

**2:20 The architect (tab 4, dashboard rules tabs, or the kit folder).**
"The rulebook is a W&B artifact. v1 by Qwen, v2 by DeepSeek, v4 by ARIA. You can diff every version
and read the misses that produced it."

**2:45 Close.**
"Agents drift. Usually a person notices. Here the loop noticed, on unseen data, before anyone was
disappointed. That's what we built."

## 2-minute speech over the diagram (docs/helix-flow.html)

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

## What is on each screen, so you can answer anything pointed at

**Lead Lab (localhost:2719).** One run on one CSV.
- Header: dataset, survivors, killed, rules version, seconds.
- Survivors table: lead id; shape (single gene, family, pathway, global, data quality); claim (the
  scout's sentence); why new (the scout's argument that this isn't already known); next step (the
  cheapest experiment to falsify it); padj (smallest adjusted p-value among the genes cited, from the
  table; below 0.05 is significant; blank for pathway claims); critic (the one-sentence justification).
- Killed table: reason code (one of six: contradicted, underpowered, confound, untestable,
  no_mechanism, already_known); claim; critic reason; padj.
- Accordion: the summary the scout read, and the rules text the critic applied.

**Traces (W&B, filter All Ops to Critic.judge).** One row per verdict.
- inputs: claim, why_not_known, next_step, table_facts (the numbers code attached), dataset header,
  sample_flags, rules (full text the critic read).
- output: label, confidence, reason.
- The parent rows named "holdout rules_v2" etc. are evaluations; their child rows are the same verdicts
  made during scoring. Nested calls named openai.chat.completions.create are the raw model requests.

**Evals (W&B).** One row per rules version per labelled set.
- Sets: holdout (90 unseen scout leads), nasa_OSD-255 (34 claims from the retina paper),
  nasa_OSD-467 (20 claims from the bone paper, never trained on).
- kill_match: false_kill (labelled ok, critic killed), kill_correct, missed_kill (labelled bad, critic
  passed). reason_match: the critic chose the same reason code as the label.
- model column: CriticModel:vN is Weave's version of the wrapper object, not the rules version. The
  row name carries the rules version.
- Compare: tick rows, press Compare, one bar chart per scorer output.

**Dashboard (localhost:2718).** The training loop from local results.
- Score per iteration; the misses handed to the architect each round; a tab per rules version with the
  full text. Neither W&B page shows the rules text or the misses.

## Numbers to have in your head

| | v0 | v1 | v2 (ships) | v4 (ARIA, overfit) |
| :--- | :--- | :--- | :--- | :--- |
| Holdout false kills | 7 | 8 | 10 | 15 |
| Holdout missed kills | 20 | 13 | 8 | 8 |
| Holdout total mistakes | 27 | 21 | 18 | 23 |
| Train reason accuracy | 0.67 | 0.74 | 0.81 | 0.84 |
| NASA false kills (54 claims) | 0 | 0 | 0 | 0 |

Read the second-to-last row against the first three: train went up at v4, holdout went down. That gap is
the catch.

## Before the room

- Restart both marimo servers; marimo does not reload the helix package.
- Run Lead Lab once and leave the result up. Never run live: 100 s is a third of the slot.
- Traces tab filtered to Critic.judge and saved as a view.
- Evals tab with the four holdout rows ticked and Compare open. Delete the N/A row.
- README "Results so far" open as the fallback if the network dies.

## Questions a judge will ask

- *Why trust the critic?* Zero false kills on 54 claims from two published NASA papers, one study never
  trained on, plus the holdout numbers that prove it isn't a rubber stamp.
- *Which is right when the paper and GeneLab disagree?* "We don't know, and the tool doesn't claim to.
  It reports what this table shows and flags the disagreement. GeneLab does not reproduce 13 of the
  bone paper's confirmed genes; that's a finding."
- *Why not let the scout use the rules and skip the critic?* "The scout never sees the table rows; code
  looks them up only after the scout names a gene. And a self-graded scout has no kill list."
- *Did the loop actually improve anything?* "Holdout total mistakes 27, 21, 18 across v0, v1, v2. Then v4
  went back to 23, and the holdout gate is what stopped it shipping."
- *How much does a run cost?* About 100 seconds and 60 critic calls per table, plus one scout call.
