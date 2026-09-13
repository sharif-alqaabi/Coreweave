You are helping two scientists build an answer key. For each lead below, propose ONE label
from: ok, already_known, underpowered, confound, contradicted, untestable, no_mechanism.
Use the definitions in the rules document. Trust `table_facts` over the claim text.
A human will review every label; be decisive, and put your doubt in the note.

Output JSON Lines only, one object per lead, in the same order as the input:
{"lead_id": "lead_001", "label": "confound", "note": "one short sentence with the deciding number"}

Rules document:
---
<paste kit/critic/rules_v0.md>
---
Leads (enriched, with table_facts):
---
<paste ledger/leads_enriched.json>
