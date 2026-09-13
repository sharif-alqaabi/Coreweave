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
The effect rests on very low counts or a weak p-value. Threshold: mean count in the higher group below 20, or padj between 0.01 and 0.05 with carriers below 4/6. Applies to OSD-104_lead_022 (mean_count=7), OSD-255_lead_042 (mean_count=12), OSD-467_lead_045 (mean_count=15), and others listed. Fixes: OSD-104_lead_022, OSD-255_lead_042, OSD-467_lead_045.

## contradicted
`table_facts` disagree with the claim: wrong direction, gene not in the table, padj above 0.05, or the scout's quoted numbers do not match the table. Applies to OSD-467_lead_031 (Stfa1/3 not significant), OSD-467_lead_034 (Glra3/Kcnq5 padj>0.05), OSD-467_lead_042 (Extl2 padj=0.80), OSD-467_lead_014 (Glra3 padj=0.98), and OSD-467_lead_009 (Apol11a padj=0.21).

## already_known
The claim restates the dataset's headline (e.g., muscle structure genes change in a muscle atrophy model) without a new angle, or `why_not_known` is missing. Applies to OSD-104_lead_048, OSD-104_lead_041, OSD-104_lead_038, and OSD-104_lead_037—all citing expected GO enrichments.

## untestable
Apply before `ok`: a concrete next step cannot rescue a claim whose core inference is absent from `table_facts`. Kill descriptive/global restatements presented as insight, non-significant trends promoted to a meaningful signal, “housekeeping-like” behavior inferred only from stable detection, and “technical reliability” inferred from one stable pseudogene. Do not apply to explicit reproducibility/data-quality checks supported by multi-gene carrier or null-gene patterns. Fixes: OSD-255_lead_058, OSD-255_lead_053, OSD-467_lead_054.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies only to claims proposing a biological mechanism, not data-quality or annotation-related claims. Fixes: OSD-255_lead_055, OSD-467_lead_048.

## examples
underpowered: S100a14 and Calhm4 upregulated | mean counts 11 and 8
no_mechanism: Gm5532 strongly regulated | no known function
already_known: high mean count genes significant | expected in RNA-seq
confound: Krt35 upregulated | carriers 2/6, both flagged
untestable: median |log2fc| 0.28 | no testable next step
contradicted: Stfa1/3 upregulated | padj>0.05
ok: Hmga1b dropout in all HU samples | clear data issue
untestable: no gene family with 3+ top hits | global claim
