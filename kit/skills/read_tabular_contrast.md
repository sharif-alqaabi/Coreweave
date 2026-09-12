# Read a tabular contrast and extract only statistically backed leads

1. Identify the contrast columns (e.g. log2FC, p-value, q-value / FDR).
2. Filter to rows with q < 0.05 (or the dataset's stated threshold). Do not relax it.
3. For each candidate row, record the row id, effect size, and the exact column names used.
4. Cross-check the row against prior ledger claims before proposing.
5. Emit a lead only if steps 2–4 all pass; otherwise log why it was dropped.
