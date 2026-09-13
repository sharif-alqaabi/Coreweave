# Critic rules v0

You judge one lead at a time. Pick exactly one option. Trust `table_facts` over `scout_evidence`
when they disagree. Numbers in `table_facts` come from the data; the scout's numbers are a copy.

## ok
No rule below applies. The claim is supported by the numbers, is not a textbook result,
and names a concrete next step.

## confound
The signal comes from a minority of samples, or from samples listed in `sample_flags`.
Threshold: carriers below half of the group (e.g. 2/6). Example: Krt17, carriers 2/6,
both carriers flagged.

## underpowered
The effect rests on very low counts or a single gene with a weak p-value.
Threshold: mean count in the higher group below 20, or padj between 0.01 and 0.05 with
carriers below 4/6. Example: Fermt1, mean count 7.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above
0.05, or the scout's quoted numbers do not match the table.

## already_known
`why_not_known` does not give a reason, or the claim restates the dataset's headline
(e.g. "muscle structure genes change in a muscle atrophy model") without a new angle.

## untestable
A lead that only restates a statistic ('gene X is reliably detected', 'median |log2fc| is 0.36') with no biological or methodological claim is untestable, as is a vague or missing next_step.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated
function (predicted genes, "Gm" prefix, or GENENAME unknown).
