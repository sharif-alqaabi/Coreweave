# ARIA in the Helix loop (confirmed 2026-09-12 with ARIA itself)

ARIA cannot connect to a custom MCP server today, and Automation-created ARIA conversations
have only W&B-provisioned tools. So:

- **Architect = our orchestrator.** `loop.py` runs the critic, scores it, logs to W&B, and
  calls Claude (`helix/reflect.py`) to write rules_v{n+1}.md through the guardrails.
  `helix/mcp_server.py` stays as the tool surface for any MCP-capable agent (Claude Code,
  Claude Desktop) to drive the same step; ARIA is not one of them yet.
- **Analyst = ARIA.** A W&B Automation triggers ARIA when an iteration run finishes. ARIA
  reads the run's `evaluation/hypotheses` table and the `critic-rules` artifact, diagnoses
  the misses, and proposes a patch in its conversation. That analysis is the demo moment.
  If a human pastes its "## section" blocks into `patches/iter{n}.md` before the loop's next
  pass, the loop applies ARIA's patch instead of Claude's.

## Setup (W&B side)
1. Project `helix` (exists, empty). Put `WANDB_PROJECT=helix` in `.env`.
2. Automation: event = run finished, filter `job_type = critic-iteration`
   (or metric `screening/eval_complete == 1`); action = Trigger ARIA; prompt below.
3. Run `python3 loop.py --iterations 4`. Each iteration logs one run + one artifact version.

## Automation prompt (paste into the Trigger ARIA action)

Run ${run_name} (job_type critic-iteration) in project ${project_name} just finished.
It is iteration N = config `iteration` of the Helix critic loop, judged with rules
artifact `critic-rules:iteration-NNN`.

1. Open this run's table `evaluation/hypotheses`. List rows where `critic_reason_code` !=
   `human_reason_code`. Group by (human, critic) pair; one sentence per pattern citing
   hypothesis_ids and the numbers in `table_facts`.
2. Compare `screening/kill_precision` and `screening/false_kill_rate` with the previous
   critic-iteration run. Did the last rules change help, hurt, or do nothing?
3. Read `rules.md` in the `critic-rules` artifact this run used. Propose a patch fixing the
   largest miss group without breaking currently-correct rows. Output the patch as:

   ## <section: ok | already_known | underpowered | confound | contradicted | untestable | no_mechanism>
   <full replacement text, citing the hypothesis_ids it fixes>

   At most 2 sections. Then one sentence on regression risk.
4. Flag any row where the human label itself looks inconsistent with `table_facts`.

## Demo flow (3 minutes)
iteration runs (seconds) -> marimo chart updates -> switch to W&B: ARIA's diagnosis appears
-> show the rules diff the loop wrote -> next iteration -> chart rises -> holdout number.
