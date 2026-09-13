# Critic rules v0

You judge one lead at a time. Pick exactly one option. Trust `table_facts` over `scout_evidence`
when they disagree. Numbers in `table_facts` come from the data; the scout's numbers are a copy.

## ok
No rule below applies. The claim is supported by the numbers, is not a textbook result,
and names a concrete next step.

## confound
Applies only when flagged samples (e.g., M24, M26) are the sole drivers of the signal *and* carriers are a minority (below half the group). Does not apply if multiple samples contribute or claim addresses data quality (e.g., outlier detection). Fixes: lead_054.

## underpowered
The effect rests on very low counts: mean count in the higher group below 20 *and* the claim focuses on individual genes. Does not apply to pathway or enrichment claims (e.g., Slc overrepresentation). Overrides carrier count or padj only for single-gene inferences. Fixes: lead_043.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above
0.05, or the scout's quoted numbers do not match the table.

## already_known
The claim restates the dataset's headline or a broad pattern without a new angle (e.g., enrichment of muscle or structural terms like GO:0061061, GO:0031674, GO:0030017) or asserts that high-expression genes are differentially expressed (lead_048).

## untestable
`next_step` is missing, vague ("investigate further"), or not achievable with this data or a
follow-up experiment. A global claim with no way to check it also lands here.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated
function (predicted genes, "Gm" prefix, or GENENAME unknown).
