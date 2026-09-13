# ARIA in the Helix loop

ARIA cannot connect to a custom MCP server today, and Automation-created ARIA conversations
have only W&B-provisioned tools. But ARIA can run Python and write to W&B, and the loop can
read W&B. So ARIA is a **third architect**: it writes its patch onto the iteration's run
(summary field `aria/patch`, or run Notes), and `loop.py --wait-for-aria 120` reads it, tests
it on all train leads, and adopts it if it beats the two model architects. Verified on the loop
side (helix/aria_channel.py reads both channels). Whether ARIA can write there: TEST FIRST
with the one-off prompt below.

## One-off test prompt (paste into ARIA in the browser)
"In project Helix, find the most recent run whose name starts with iter-003. Using Python and
the wandb API, set that run's summary field `aria/patch` to the string
'## untestable\nchannel test from ARIA\n' and call summary.update(). If you cannot run code,
put that same text into the run's Notes. Then tell me which you did."
Then check: python3 -c "from helix.aria_channel import fetch_aria_patch as f; print(f('<run_id>', 3, 5))"

So:

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
   largest miss group without breaking currently-correct rows. Write the patch as:

   ## <section: ok | already_known | underpowered | confound | contradicted | untestable | no_mechanism | examples>
   <full replacement text, citing the hypothesis_ids it fixes>

   At most 3 sections, each under 90 words. Humans' labels are ground truth: never add an
   exception that lets the critic keep its current answer.
4. WRITE THE PATCH BACK so the loop can test it. Run Python:
       import wandb; api = wandb.Api(); run = api.run("${project_name}/${run_id}")
       run.summary["aria/patch"] = <the patch text>; run.summary.update()
   If you cannot run code, put the patch text in this run's Notes field instead.
   The loop polls the run, tests your patch on all 90 train leads against two other architects,
   and adopts it only if it scores best. Your patch's fate is visible in the next run's config.
5. Reply with: the patterns you found, the sections you changed, and one sentence on regression risk.

## Demo flow (3 minutes)
iteration runs (seconds) -> marimo chart updates -> switch to W&B: ARIA's diagnosis appears
-> show the rules diff the loop wrote -> next iteration -> chart rises -> holdout number.
