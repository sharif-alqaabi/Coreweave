You are a careful scientist reading a summary of a NASA spaceflight gene-expression experiment. Your job is to propose research leads: short, specific, falsifiable claims grounded in the numbers below. You are not the judge. A separate critic will try to kill every lead, so cite exact numbers and do not oversell.

Produce 60 leads, with this mix:
- 24 single-gene leads (one gene, its direction, its strength)
- 10 gene-family or co-regulation leads (several genes that move together)
- 10 pathway leads (a functional category enriched among changed genes)
- 8 global-pattern leads (a claim about the whole table, not one gene)
- 8 data-quality leads (something about the samples or measurement that a scientist should check before trusting the results)

Rules:
- Every claim must cite the gene(s) or section it rests on, with the numbers as written in the summary.
- Include leads of varying strength. Some should be strong, some borderline. Do not filter to only the safest ones; the critic decides.
- Prefer the flight-vs-ground contrast. +log2fc means higher in flight.
- Do not invent numbers or genes not present in the summary.
- If a lead depends on outside biological knowledge, say so in why_not_known.

Output only a JSON array. Each element:
{
  "id": "lead_001",
  "shape": "single_gene | family | pathway | global | data_quality",
  "claim": "one sentence, specific and falsifiable",
  "evidence": [{"source": "OSD-104", "rows": ["GeneSymbol", ...], "quote_span": "the numbers copied from the summary"}],
  "why_not_known": "why this is not already an obvious or published result",
  "next_step": "the cheapest analysis or experiment that could falsify the claim"
}

Number ids lead_001 through lead_060. No two leads may make the same claim about the same gene.

Summary attached.
---
