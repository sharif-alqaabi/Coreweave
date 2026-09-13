# Helix: demo script and submission notes (13 Sep 2026)

## Submission form

**Project name:** Helix

**Description (2-3 sentences):**
Helix reads a NASA OSDR gene-expression table, proposes research leads, and lets a separate critic
kill the weak ones with a stated reason. After every round an architect rewrites the critic's rulebook
from the misses, and candidate rulebooks fight a tournament before promotion. The loop is self-improving
because the rules are versioned artifacts that change the critic's behaviour, and every version is scored
on unseen leads and on claims transcribed from published NASA papers, so a bad rewrite gets caught.

**Track:** Best Use of Weave (primary). Also eligible for Best Loop Design. See "Tracks" below before
choosing ARIA or marimo.

**Demo:** run `marimo run app/lead_lab.py` and upload any `*_differential_expression.csv` from
`data/raw/`. About 100 s per run. The W&B Evals tab shows the trained-versus-untrained comparison
without any setup.

## 3-minute script (rehearse with a timer; cut, don't rush)

**0:00 - 0:30, the problem, no slides.**
"NASA has 243 gene-expression studies from spaceflight mice. A scientist can't read them all, and an
LLM that reads them invents findings, because nothing in the loop is allowed to say no. Helix is a loop
where saying no is a separate job, and the rules for saying no get rewritten every round."

**0:30 - 1:15, Lead Lab, already loaded with a finished run.**
Show the survivors table, then the killed table. Read one kill aloud, for example an underpowered one:
"mean count 15 in the higher group, below the threshold of 20." Point out the padj column: every
verdict cites a number from the table, attached by code, not by the model.

**1:15 - 2:00, the loop, W&B Evals tab.**
Show the rows v0, v1, v2, v4 on the holdout. Say: "v0 is the untrained critic. It waves through 20 bad
leads. Each rewrite catches more junk. v4 scored best on training data and worse on unseen data, and we
caught that because we score every version on a holdout. We ship v2." Then click the two NASA rows:
"These are claims transcribed from the studies' published papers. Zero published findings killed, by
any version, and every unsupported claim killed with the number that decided it."

**2:00 - 2:40, what makes it self-improving.**
Show `kit/critic/` and the meta files: v1 by Qwen, v2 by DeepSeek, v4 by ARIA. "Three architects
propose patches from the misses; the tournament promotes the one that scores best. The rulebook is a
versioned W&B artifact, so you can diff what changed and why."

**2:40 - 3:00, the honest line.**
"What we learned: a rulebook can overfit in four rounds, and a critic that only agrees with LLM
labels isn't trustworthy until it also passes real published science. Both checks are in the repo."

## Before the room

- Restart both marimo servers (`marimo run app/lead_lab.py -p 2719`, `marimo run app/dashboard.py -p 2718`).
  Marimo does not reload the `helix` package when it changes.
- Run Lead Lab once on a CSV from `data/raw/` and leave the result on screen. Do not run live in the room;
  100 s is a third of the slot.
- Open the W&B Evals page in a second tab, sorted by name, the broken N/A row deleted or hidden.
- Have `README.md` "Results so far" open as the fallback if the network dies.

## Questions a judge will ask

- *Why trust the critic?* Zero false kills on 54 claims from two published NASA papers, one study never
  trained on, plus the holdout numbers that prove it isn't a rubber stamp.
- *Which is right when the paper and GeneLab disagree?* "We don't know, and the tool doesn't claim to.
  It reports what this table shows and flags the disagreement. GeneLab does not reproduce 13 of the
  bone paper's confirmed genes; that's a finding."
- *Why not let the scout use the rules and skip the critic?* "The scout never sees the table rows;
  code looks them up only after the scout names a gene. And a self-graded scout has no kill list."
- *Did the loop actually improve anything?* "Holdout total mistakes: 27, 21, 18 across v0, v1, v2.
  Then v4 went back to 23, and the holdout gate is what stopped it shipping."
