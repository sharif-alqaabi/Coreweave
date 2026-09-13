"""Research knowledge graph: findings, entities, passages, and the typed relationships between them.

    corpus    -> OSDR study descriptions + PubMed abstracts + PMC open-access full text, cut into passages
    entities  -> genes / GO terms / tissues / datasets / papers found in findings and passages (code + Jev for ambiguity)
    edges     -> candidate pairs from shared entities; TypeSafe (Jev) judges the relationship of each pair
    explain   -> a regular LLM writes one sentence per accepted edge, quoting the passage
    build     -> runs the stages and writes results/graph.json
"""
