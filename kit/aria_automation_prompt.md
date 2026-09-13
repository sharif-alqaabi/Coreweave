# ARIA as the architect, via MCP

## Verify before relying on it (ARIA's own checklist, in order)
1. Does ARIA have an "add custom MCP server" facility? Find the screen. If not, use the fallback below.
2. In an interactive ARIA chat, ask it to call `get_rules`. Expect {version, digest, text}.
3. Ask it to call `propose_rules_patch` with a harmless patch, then `apply_rules_patch` with the
   digest from step 2. Expect {written, version, digest}. Delete the test version afterwards.
4. Create the Automation (below), trigger it with a test run, and confirm the automation-created
   conversation can still see the Helix tools. This is the decisive test.
5. Run ONE cycle: loop iteration 0 -> automation -> rules_v1 -> iteration 1. Then all four.

## One-time setup
- `export HELIX_MCP_TOKEN=<random string>`; start `python3 helix/mcp_server.py`
- `cloudflared tunnel --url http://localhost:8765` -> copy the https URL
- In ARIA, add the custom MCP server at `https://<host>/mcp`
- W&B Automation: event = run finished, filter job_type = critic-iteration
  (or metric `screening/eval_complete` == 1); action = Trigger ARIA; prompt below.
  Do NOT trigger on the critic-rules artifact: it fires before evaluation is logged.
- Run `python3 loop.py --iterations 4 --wait-for-aria 180` only after step 4 passed.

## Automation prompt (paste into the Trigger ARIA action)

Run ${run_name} (job_type critic-iteration) in project ${project_name} just finished.
You are the architect of the Helix critic loop. Use the Helix MCP tools.

1. Read this run's config `iteration` = N. Call `get_misses` with iteration=N (not "latest").
   Group misses by (human_reason_code, critic_reason_code); one sentence per pattern, citing
   hypothesis_ids and the numbers in table_facts.
2. Call `list_iterations` and say whether precision rose or fell versus iteration N-1.
3. Call `get_rules` (latest). Keep its `digest`.
4. Choose ONE or TWO sections whose rewrite fixes the largest miss group without breaking
   leads currently correct. Write the patch as "## <reason_code>\n<full replacement text,
   citing the hypothesis_ids it fixes>".
5. Call `propose_rules_patch` with the patch. If error, fix and retry.
6. Call `apply_rules_patch` with patch, change_reason (one sentence), base_rules_digest =
   the digest from step 3, iteration = N, source_run_id = this run's id, token = <HELIX_MCP_TOKEN>.
   If it reports a stale digest, stop: another conversation already revised the rules.
7. Reply with the patterns, the sections changed, and the precision you expect at N+1.

Valid sections: ok, already_known, underpowered, confound, contradicted, untestable, no_mechanism.

## Fallback if ARIA cannot reach custom MCP (demo-safe)
Run `python3 loop.py --iterations 4` without --wait-for-aria. The loop's own architect
(Claude, helix/reflect.py) writes each patch through the same guardrails. Trigger ARIA on run
finished anyway with steps 1-4 only, so its independent diagnosis appears in W&B for the demo.
