# Helix

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Researchers are the primary users. The current implemented domain is space biology: researchers inspect NASA OSDR differential-expression tables, evaluate hypotheses, and check evidence across studies and papers.

The presentation audience is CoreWeave and hackathon judges from FAANG companies. They evaluate the working product and its technical execution; they are distinct from the researchers who use it.

## Product Purpose

Turn scientific tables into research leads with inspectable evidence and rejection reasons. Help researchers identify leads worth investigating, understand why others fail, and assess whether surviving signals appear in other studies.

Success means useful, traceable hypotheses and demonstrable improvements on unseen evaluation data. Model verdicts and cross-study evidence checks are not experimental validation.

## Positioning

Helix separates proposing leads, judging them against code-attached numbers, and rewriting the critic's rules. Rule changes are evaluated on held-out leads to catch regressions before selecting a rulebook for use.

TypeSafe is an implemented product capability, not an optional or speculative add-on. It supports cross-study verification and typed evidence relationships in the research graph. It supplements the critic's verdicts without changing historical holdout scores or saved survival counts.

## Operating Context

- Researchers use Lead Lab to upload a differential-expression CSV or inspect a saved run, review survivors and rejected leads, and run TypeSafe verification.
- Research Graph Lab exposes connections among findings, passages, papers, datasets, and biological entities, with scored relationships and supporting evidence.
- The browser-based presentation demonstrates the problem, loop, product, rulebook comparisons, evaluation evidence, judged findings, and TypeSafe results.
- The slide deck is the current delivery priority. Preserve its working core when integrating product changes. TypeSafe's placement in a bonus tab is a presentation choice, not its status in the product.
- Saved results keep the presentation independent of live inference calls. Fresh verification and graph builds can require API access and downloaded scientific data.

## Capabilities and Constraints

- Python and Marimo implement the current interfaces. Preserve the existing stack unless a change is requested.
- `app/deck.py` is the presentation source. `scripts/build_deck_site.py` generates `app/deck_site.py`; do not maintain conflicting edits in the generated file.
- `app/deck.css`, `docs/helix-flow.html`, and `docs/helix-charts.html` support the deck. Static export goes to `site/`; export from `app/` to resolve its stylesheet.
- `app/lead_lab.py`, `helix/replicate.py`, `app/graph_lab.py`, and `helix/graph/` contain the implemented verification and graph workflows.
- TypeSafe scores semantic relationships and study comparability; code supplies numerical checks and acceptance gates.
- Preserve the baseline demo, rulebook comparison controls, saved findings, and evaluation data during integrations.
- Keep presentation attributions distinct from experiment provenance. The current deck uses user-requested model attributions that differ from the original metadata; those labels are not evidence of historical authorship. Do not rewrite experimental records to match presentation copy.

## Brand Commitments

The product name is Helix. Explain capabilities concretely for researchers and a technically informed presentation audience. No new visual direction was requested during initialization; existing UI remains the authority for refinements.

## Evidence on Hand

- Saved baseline and product runs: `results/naive_OSD-255.json` and `results/product_OSD-421.json`.
- Saved TypeSafe verification: `results/replicate_OSD-421.json`. It covers the 38 OSD-421 survivors; 35 have a replication signal in at least one comparable table and 3 were not replicated in the tables checked. These counts describe that saved run.
- Saved research graph: `results/graph.json`, including typed relationships and graph statistics.
- Rulebooks and original provenance: `kit/critic/rules_v*.md` and accompanying metadata.
- Evaluation results in `results/`, with W&B/Weave evidence links in the presentation.
- Do not invent customers, endorsements, clinical validation, performance measurements, or scientific discoveries.

## Product Principles

1. Make evidence and rejection reasons inspectable.
2. Measure rule improvements on unseen data, not just training performance.
3. Treat cross-study verification as a working part of the research workflow.
4. Preserve the reliable presentation while integrating product improvements.
5. Keep hypotheses, model judgments, numerical evidence, and experimental validation distinguishable.

## Open Decisions

No product-specific accessibility standard or additional researcher personas were established in this initialization.
