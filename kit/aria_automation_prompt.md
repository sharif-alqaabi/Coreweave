# ARIA as the architect, via MCP

## One-time setup
1. Start the Helix MCP server on the demo machine:  `python3 helix/mcp_server.py`
2. Expose it:  `cloudflared tunnel --url http://localhost:8765`  -> copy the https URL it prints.
3. In ARIA, add a custom MCP server with URL `https://<that-host>/mcp` (no auth).
   Verify by asking ARIA: "call get_rules" -> it should return the rules text.
4. Create a W&B Automation: event = new version of artifact `critic-rules`,
   action = Trigger ARIA, prompt = the block below.
5. Run the loop with `python3 loop.py --iterations 4 --wait-for-aria 180`.

## Automation prompt (paste into the Trigger ARIA action)

A new iteration of the Helix critic loop finished in project ${project_name}.
You are the architect. Improve the critic's rules using the Helix MCP tools.

1. Call `list_iterations` to see precision per iteration. Note the latest iteration number N.
2. Call `get_misses` with iteration=N. Group the misses by (human_reason_code, critic_reason_code)
   and describe each pattern in one sentence, citing hypothesis_ids and the numbers in table_facts.
3. Call `get_rules` to read the current rules. Optionally `get_dataset_summary` for context.
4. Decide the ONE or TWO sections whose rewrite would fix the largest group of misses without
   breaking leads the critic currently gets right.
5. Call `apply_rules_patch` with `patch` = those sections in the format
   "## <reason_code>\n<full replacement text, citing the hypothesis_ids it fixes>"
   and `change_reason` = one sentence. If the tool returns an error, fix the patch and call again.
6. Reply with: the patterns you found, the sections you changed, and the precision you expect
   next iteration.

Valid section names: ok, already_known, underpowered, confound, contradicted, untestable, no_mechanism.

## Fallback if MCP is unavailable on stage
Ask ARIA the same prompt without step 5; paste its "## section" output into
`patches/iter{N}.md`; the loop applies it on its next pass.
