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
Threshold: mean count in the higher group below 20, or padj between 0.01 and 0.05 with carriers below 4/6.  
Example: Fermt1, mean count 7. Applies to individual genes or claims aggregating genes with low expression.  
(fixes: lead_057, lead_030) — specifically, lead_030 is correctly flagged as underpowered due to mean counts of 11 and 8, both below 20, despite strong padj and carrier counts.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above
0.05, or the scout's quoted numbers do not match the table.

## already_known
A claim is already_known if it restates expected biology without leveraging enrichment to propose a novel, testable mechanism. However, if the pathway enrichment (e.g., GO:0061061, GO:0031674, GO:0030017) is used to justify a specific downstream assay (e.g., satellite cell activation, Ttn isoforms, passive tension), it is *not* already_known. (fixes: lead_048, lead_041, lead_038, lead_037)

## untestable
`next_step` is missing, vague ("investigate further"), or not achievable with this data or a
follow-up experiment. A global claim with no way to check it also lands here.

## no_mechanism
The numbers hold but the claim offers no biological mechanism *and* the gene lacks annotated function (e.g., "Gm" prefix, predicted, or unknown). This does not apply if the gene has known function or belongs to a characterized family. (fixes: lead_050)
