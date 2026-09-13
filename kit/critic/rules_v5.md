# Critic rules v0

You judge one lead at a time. Pick exactly one option. Trust `table_facts` over `scout_evidence`
when they disagree. Numbers in `table_facts` come from the data; the scout's numbers are a copy.

## ok
No rule below applies. The claim is supported by the numbers, is not a textbook result,
and names a concrete next step.

## confound
Signal driven by minority carriers (below half the group) or flagged samples. Applies when carriers ≤3/6 and influence is concentrated, even if mean counts are moderate. Fixes OSD-104_lead_013 (Krt35: 3/6 carriers, all unflagged but still minority-driven) and OSD-467_lead_044 (Cyp2b10: tissue uncertainty doesn’t override carrier imbalance). Does not apply if carriers ≥4/6 and no flags.

## underpowered
Mean count in the higher group below 20, or padj between 0.01–0.05 with carriers <4/6. Applies to OSD-104_lead_030 (S100a14:11, Calhm4:8), OSD-104_lead_022 (Msx2: padj=5.2e-03, mean=19), OSD-255_lead_042 (GO:0035967: padj=0.02, carriers=3/6), OSD-467_lead_045 (7 sig genes), and OSD-467_lead_024 (Rskr: mean=18). Threshold lowered to catch low-expression signals even if carriers ≥4/6 when mean <20.

## contradicted
`table_facts` disagree: wrong direction, gene not present, padj >0.05, or scout numbers mismatch. Applies to OSD-467_lead_031 (Stfa1/Stfa3 up—table shows padj>0.05), OSD-467_lead_034 (Glra3/Kcnq5 up—Glra3 padj=0.98), OSD-467_lead_014 (Glra3 log2fc=+0.17, padj=0.98—not significant), and OSD-467_lead_009 (Apol11a log2fc=-1.34, padj=0.21—not significant).

## already_known
The claim restates the dataset’s headline (e.g., muscle structure genes change in atrophy) or a general pattern without novel context. No new biological insight. Applies to OSD-104_lead_048 (high-count genes DE—expected), OSD-104_lead_041 (muscle development genes enriched—textbook), OSD-104_lead_038 (I band genes enriched—expected), and OSD-104_lead_037 (sarcomere genes enriched—routine).

## untestable
No feasible next step or claim cannot be validated with data. Applies to median log2fc interpretations (OSD-255_lead_060, OSD-255_lead_045), stability claims without testable predictions (OSD-467_lead_033, OSD-467_lead_052), broad negatives (OSD-467_lead_049), and consistency without significance (OSD-467_lead_059). Requires concrete, falsifiable follow-up.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies to OSD-104_lead_050 (Gm5532), OSD-467_lead_023 (Gm11266).

## examples
ok: Meiosin in 8/9 controls — unexpected in somatic tissue | carriers=8/9  
ok: Hmga1b log2fc=-5.10 — strongest downregulation | log2fc=-5.10  
confound: Krt35 up in 3/6 space samples | carriers=3/6  
untestable: median |log2fc|=0.28 implies fold-change thresholds miss signals | median=0.28  
untestable: no gene family has ≥3 members in top hits | count=2 max  
untestable: Rps11-ps2 stable expression suggests housekeeping | padj=0.99  
underpowered: rRNA n-R5s118 log2fc=+1.13, padj=0.099 | padj=0.099, mean=?  
contradicted: Stfa1 up — but padj>0.05 | padj=0.12
