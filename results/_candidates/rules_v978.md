# Critic rules v0

You judge one lead at a time. Pick exactly one option. Trust `table_facts` over `scout_evidence`
when they disagree. Numbers in `table_facts` come from the data; the scout's numbers are a copy.

## ok
No rule below applies. The claim is supported by the numbers, is not a textbook result,
and names a concrete next step.

## confound
Signal driven by minority carriers (below half the group) or flagged samples. Applies when carriers <50% even if mean ≥20. Fixes OSD-104_lead_013 (Krt35, 3/6 carriers) and OSD-467_lead_044 (Cyp2b10, low carrier support). Does not apply if all or nearly all samples carry the signal. Excludes data-quality claims about sample outliers (e.g., OSD-104_lead_054).

## underpowered
Mean count in the higher group below 20, or padj between 0.01–0.05 with carriers <4/6. Applies to OSD-104_lead_030 (S100a14:11, Calhm4:8), OSD-104_lead_022 (Msx2: padj=5.2e-03, mean=19), OSD-255_lead_042 (GO:0035967: padj=0.02, carriers=3/6), OSD-467_lead_045 (7 sig genes), and OSD-467_lead_024 (Rskr: mean=18). Threshold lowered to catch low-expression signals even if carriers ≥4/6 when mean <20.

## contradicted
`table_facts` disagree: wrong direction, gene not present, padj >0.05, or scout numbers mismatch. Applies to OSD-467_lead_031 (Stfa1/Stfa3 up—table shows padj>0.05), OSD-467_lead_034 (Glra3/Kcnq5 up—Glra3 padj=0.98), OSD-467_lead_014 (Glra3 log2fc=+0.17, padj=0.98—not significant), and OSD-467_lead_009 (Apol11a log2fc=-1.34, padj=0.21—not significant).

## already_known
The claim restates the dataset’s headline (e.g., muscle structure genes change in atrophy) or a general pattern without novel context. No new biological insight. Applies to OSD-104_lead_048 (high-count genes DE—expected), OSD-104_lead_041 (muscle development genes enriched—textbook), OSD-104_lead_038 (I band genes enriched—expected), and OSD-104_lead_037 (sarcomere genes enriched—routine).

## untestable
No feasible next step or claim cannot be tested with available data. Applies when the claim describes global patterns without testable predictions (e.g., "most signals are subtle"), or asserts stability/lack of change without a proposed validation. Fixes OSD-255_lead_060, OSD-255_lead_048, OSD-255_lead_045, OSD-467_lead_033, OSD-467_lead_052, OSD-467_lead_049, OSD-467_lead_059.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated function (predicted genes, "Gm" prefix, or GENENAME unknown). Applies to OSD-104_lead_050 (Gm5532), OSD-467_lead_023 (Gm11266).

## examples
ok: Sample M26 shares outlier status with M24 | 4/50 top genes, carriers 2/6 or 3/6  
confound: Krt35 up in 3/6 flight samples | carriers <50%  
untestable: Median |log2fc|=0.28 implies most changes missed by fold thresholds | no testable prediction  
untestable: Upregulated genes have higher counts in flight | global claim, no next step  
ok: Meiosin expressed in 8/9 controls, unexpected in somatic tissue | biological anomaly  
ok: Hmga1b most downregulated gene, log2fc=-5.10 | strong, specific signal  
underpowered: rRNA gene n-R5s118, padj=0.099, log2fc=+1.13 | near-significant, low power  
contradicted: Stfa1/Stfa3 up—table shows padj>0.05 | direction mismatch
