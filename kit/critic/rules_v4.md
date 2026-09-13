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
Mean count in the higher group below 20, or padj between 0.01–0.05 with carriers <4/6. Applies to OSD-104_lead_030 (S100a14:11, Calhm4:8), OSD-104_lead_022 (Msx2: padj=5.2e-03, mean=19), OSD-255_lead_042 (GO:0035967: padj=0.02, carriers=3/6), OSD-467_lead_045 (7 sig genes), and OSD-467_lead_024 (Rskr: mean=18). Threshold lowered to catch low-expression signals even if carriers ≥4/6 when mean <20.

## contradicted
`table_facts` disagree: wrong direction, gene not present, padj >0.05, or scout numbers mismatch. Applies to OSD-467_lead_031 (Stfa1/Stfa3 up—table shows padj>0.05), OSD-467_lead_034 (Glra3/Kcnq5 up—Glra3 padj=0.98), OSD-467_lead_014 (Glra3 log2fc=+0.17, padj=0.98—not significant), and OSD-467_lead_009 (Apol11a log2fc=-1.34, padj=0.21—not significant).

## already_known
The claim restates the dataset’s headline (e.g., muscle structure genes change in atrophy) or a general pattern without novel context. No new biological insight. Applies to OSD-104_lead_048 (high-count genes DE—expected), OSD-104_lead_041 (muscle development genes enriched—textbook), OSD-104_lead_038 (I band genes enriched—expected), and OSD-104_lead_037 (sarcomere genes enriched—routine).

## untestable
`next_step` is missing, vague ("investigate further"), or not achievable with this data or a
follow-up experiment. A global claim with no way to check it also lands here.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies to OSD-104_lead_050 (Gm5532), OSD-467_lead_023 (Gm11266).
