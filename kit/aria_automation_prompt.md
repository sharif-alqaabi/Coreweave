# W&B Automation: prompt sent to ARIA when a new `critic-rules` artifact version is logged

Configure in W&B: Automations -> New -> event "artifact version created" on collection
`critic-rules` -> action "Trigger ARIA" -> paste the prompt below.

---
A new iteration of the Helix critic loop just finished in project ${project_name}.
Find the latest run with job_type "critic-iteration" and read its table `evaluation/hypotheses`.

1. List every row where `critic_reason_code` differs from `human_reason_code`. Group them by
   the (human, critic) pair and describe the pattern in one sentence per group, citing
   `hypothesis_id`s and the numbers in `table_facts`.
2. Compare `screening/kill_precision` and `screening/false_kill_rate` with the previous
   critic-iteration run. Say whether the last rules change helped, hurt, or did nothing.
3. Read the artifact `critic-rules` (file rules.md, latest version). Propose a patch that
   would fix the largest group of misses without breaking rows that are currently correct.

Output the patch ONLY in this format, changing at most 2 sections, and nothing else after it:

## <section name, one of: ok, already_known, underpowered, confound, contradicted, untestable, no_mechanism>
<full replacement text for that section; cite the hypothesis_ids it fixes>
