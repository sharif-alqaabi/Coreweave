# What a processed OSDR table looks like

`processed_table_example.csv` is 17 real rows (of 22,438) from OSD-104, mouse soleus,
6 spaceflight vs 6 ground control. Same 34 columns as the full file. Rows were picked to
show the cases a critic must tell apart:

| Rows | What they show |
|---|---|
| Dsc3, Pkp1, Spink1, Calhm4 | strongest real-looking increases in flight |
| Gcat, Gm23925, Ppp1r1c, Dhrs9 | strongest decreases in flight |
| Krt17, Krt14, Krt5 | huge fold change driven by 2 of 6 flight mice: contamination, not biology |
| Pycr3, Irak4, Ube2a, Pgm2 | no change (padj > 0.5): a lead about these should die |
| NA, NA | unannotated genes: untestable in practice |

## Columns, in four groups

1. **Identity**: `ENSEMBL`, `SYMBOL`, `GENENAME`, `REFSEQ`, `ENTREZID`, `STRING_id`,
   `GOSLIM_IDS` (broad functional categories, useful for pathway-level leads).
2. **Per-sample expression**: one column per mouse, `..._GC_Rep1_M33` (ground) and
   `..._FLT_Rep1_M23` (flight). Normalized counts; 1 means effectively zero.
3. **The comparison**: `Log2fc_(A)v(B)` fold change on log2 scale; `P.value_` raw;
   `Adj.p.value_` corrected for 22k tests (use this one); `Stat_` the test statistic.
   Each appears twice, once per direction (A vs B and B vs A); they are mirror images.
4. **Group summaries**: `Group.Mean_(X)`, `Group.Stdev_(X)`, plus `All.mean`, `All.stdev`,
   `LRT.p.value` (an overall test across groups).

## Where 60 different leads come from

A lead is not only "gene X changed". The table supports at least six shapes:

- **Single gene**: "Gcat is silenced in flight muscle." (thousands available; most are boring)
- **Gene family / co-regulation**: "Dsc3 and Pkp1, both desmosome genes, rise together."
- **Pathway** (via `GOSLIM_IDS` or gene names): "mitochondrial genes are broadly down."
- **Global pattern**: "more genes fall than rise; flight suppresses transcription overall."
- **Data-quality**: "the keratin signal is dissection contamination in 2 flight mice."
- **Dissociation**: "top fold changes come from near-zero counts, not high expression."

Ask the scout for a quota per shape, and let the critic kill duplicates and the boring ones.
