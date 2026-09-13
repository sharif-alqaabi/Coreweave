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
The effect rests on very low counts or a weak p-value. Threshold: mean count in the higher group below 20, or padj between 0.01 and 0.05 with carriers below 4/6. Applies to OSD-104_lead_057 (mean_count=13), OSD-104_lead_030 (means=11,8), OSD-255_lead_042, OSD-467_lead_045, OSD-467_lead_024, and OSD-467_lead_008.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above 0.05, or the scout's quoted numbers do not match the table. Applies to OSD-467_lead_031 (Stfa1/3 not significant), OSD-467_lead_034 (Glra3/Kcnq5 padj>0.05), OSD-467_lead_042 (Extl2 padj=0.80), OSD-467_lead_014 (Glra3 padj=0.98), and OSD-467_lead_009 (Apol11a padj=0.21).

## already_known
The claim restates the dataset's headline (e.g., muscle structure genes change in a muscle atrophy model) without a new angle, or `why_not_known` is missing. Applies to OSD-104_lead_048, OSD-104_lead_041, OSD-104_lead_038, and OSD-104_lead_037—all citing expected GO enrichments.

## untestable
Kill when a descriptive statistic is used to claim an unmeasured general property: a distribution from exemplars, housekeeping or technical reliability from padj/carriers, pathway absence from top hits, or a “consistent trend” from nonsignificance. Correlation, power, simulation, enrichment, or variance analysis proposed later does not rescue the current claim; it shows the claim is not yet established. Apply to OSD-255_lead_060, OSD-255_lead_048, OSD-255_lead_045, OSD-467_lead_059, OSD-467_lead_033, OSD-467_lead_052, and OSD-467_lead_049. Do not apply to directly measured significant changes or set-wide data-quality checks.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated
function (predicted genes, "Gm" prefix, or GENENAME unknown).
