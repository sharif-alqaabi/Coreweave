# Golden set review (two people, ~25 min)

Files: `ledger/leads_enriched.json` (the leads + true numbers), `data/golden/labels_proposed.jsonl`
(LLM proposals). Edit the proposals and save the result as `data/golden/labels.jsonl`, one line per
lead: `{"lead_id": "lead_007", "label": "confound", "note": "..."}`. Every lead needs a label.

Labels: ok, already_known, underpowered, confound, contradicted, untestable, no_mechanism.

## What the proposer gets wrong (check these first)
- **confound is over-used.** It applies when the effect comes from a minority of samples
  (carriers below half) or from flagged mice. A gene with 5/6 carriers is not a confound just
  because M24 is one of the five.
- **pathway leads on muscle-structure terms** (sarcomere, myofibril, Z disc) in a muscle
  atrophy study are probably `already_known`. Decide once, apply consistently.
- **"X is reliably detected" is not a lead.** No claim, nothing to test -> `untestable`.
- **Restating a summary statistic** ("median |log2fc| is 0.36") -> `untestable` unless it makes
  a claim about biology.
- Two leads with the same genes and same claim should get the same label.

## Tie-break
Discuss once. Still split: label `ok` and write both views in the note. Keep each person's
original label in the note (e.g. "A: confound, B: underpowered") so the disagreement is recorded.

## Then
python3 scripts/split_golden.py ledger/leads_enriched.json data/golden/labels.jsonl
