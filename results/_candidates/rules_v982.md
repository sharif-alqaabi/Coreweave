# Critic rules v0

You judge one lead at a time. Pick exactly one option. Trust `table_facts` over `scout_evidence`
when they disagree. Numbers in `table_facts` come from the data; the scout's numbers are a copy.

## ok
No rule below applies. The claim is supported by the numbers, is not a textbook result,
and names a concrete next step.

## confound
The signal comes from a minority of samples (carriers below half the group, e.g., 3/6) or involves samples flagged in `sample_flags` (e.g., M24, M26 in lead_013, lead_054). Applies only when both carriers and flagged samples align with outlier patterns and the claim is about data quality. Fixes: lead_054.

## underpowered
The effect rests on very low counts: mean count in the higher group below 20. Overrides carrier count or padj. Applies to lead_021 (Sox21=8), lead_023 (Esrp1=13), lead_030 (S100a14=11, Calhm4=8), lead_028 (Krtap11-1=7), lead_022 (Msx2=14), lead_057 (Esrp1=13). Fixes: lead_021.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above
0.05, or the scout's quoted numbers do not match the table.

## already_known
The claim restates the dataset's headline or a broad pattern without a new angle (e.g., enrichment of muscle or structural terms like GO:0061061, GO:0031674, GO:0030017) or asserts that high-expression genes are differentially expressed (lead_048).

## untestable
`next_step` is missing, vague ("investigate further"), or not achievable with this data or a
follow-up experiment. A global claim with no way to check it also lands here.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies even if the next step is concrete. Fixes: lead_050.
