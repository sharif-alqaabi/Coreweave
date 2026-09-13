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
Apply before `ok`. Kill as underpowered when an entity central to the claim has mean count below 20 in the group whose response is interpreted, including every named entity in multi-entity claims; enrichment/global claims supported by fewer than four significant genes are also underpowered. Strong padj, full carriers, novelty, or a concrete next step never override sparse support. This fixes OSD-104_lead_057, OSD-104_lead_030, OSD-104_lead_023, OSD-255_lead_042, OSD-467_lead_045, OSD-467_lead_024, and OSD-467_lead_008.

## contradicted
Use contradicted, before underpowered, when a claim asserts regulation, up/down direction, enrichment, or significance that any central cited result fails: padj above 0.05, wrong direction, absent entity, or mismatched value. Low counts do not soften unsupported regulation; correctly quoting a non-significant padj does not validate calling the gene regulated. If the untestable rule governs a trend/stability inference, use untestable. This fixes OSD-467_lead_031, OSD-467_lead_034, OSD-467_lead_042, OSD-467_lead_014, and OSD-467_lead_009.

## already_known
`why_not_known` does not give a reason, or the claim restates the dataset's headline
(e.g. "muscle structure genes change in a muscle atrophy model") without a new angle.

## untestable
The proposed next step must test the biological claim, not merely perform the analysis needed to establish it. Mark untestable when a lead generalizes from examples to “most,” “more likely,” housekeeping/reliability, pathway absence, or a non-significant trend without supporting aggregate evidence; a descriptive statistic alone is not insight. This fixes OSD-255_lead_060, OSD-255_lead_048, OSD-255_lead_045, OSD-467_lead_059, OSD-467_lead_033, OSD-467_lead_052, and OSD-467_lead_049.

## no_mechanism
The numbers hold but the claim offers no biological reason and the gene has no annotated
function (predicted genes, "Gm" prefix, or GENENAME unknown).
