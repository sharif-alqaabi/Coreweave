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
The effect rests on very low counts or a single gene with a weak p-value. Threshold: mean count in the higher group below 20, or padj between 0.01 and 0.05 with carriers below 4/6. Applies to OSD-104_lead_057 (mean_count=13), OSD-104_lead_030 (means=11,8), OSD-255_lead_042, OSD-467_lead_045 (only 7 significant genes), and OSD-467_lead_024 (Rskr downregulated, weak support).

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above
0.05, or the scout's quoted numbers do not match the table.

## already_known
The claim restates the dataset's headline or a broad pattern without a new angle (e.g., "muscle structure genes change in a muscle atrophy model"). No novel biological insight is provided. Applies to OSD-104_lead_048 (high-count genes are DE), OSD-104_lead_041, OSD-104_lead_038, and OSD-104_lead_037 (all repeat GO enrichments as findings).

## untestable
`next_step` is missing, vague ("investigate further"), or not achievable with this data or a
follow-up experiment. A global claim with no way to check it also lands here.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies to OSD-104_lead_050 (Gm5532, no function) and OSD-467_lead_023 (Gm11266, no orthologs or domains).
