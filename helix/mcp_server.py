"""Helix MCP server: the tools ARIA (or any MCP client) can call to act as the architect.

    python3 helix/mcp_server.py                 # serves http://0.0.0.0:8765/mcp
    cloudflared tunnel --url http://localhost:8765   # public URL to paste into ARIA

Tools: list_iterations, get_misses, get_rules, get_dataset_summary, propose_rules_patch,
apply_rules_patch (compare-and-swap on the rules digest; optional HELIX_MCP_TOKEN).
apply_rules_patch is the wire: ARIA writes rules_v{n+1}.md; loop.py picks it up.
"""
import csv, glob, hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.mcpserver import MCPServer
from helix.reflect import apply_patch, render_patch, MAX_SECTIONS
TOKEN = os.getenv("HELIX_MCP_TOKEN", "")            # if set, apply_rules_patch requires it


def _digest(path):
    return "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]

mcp = MCPServer("helix", instructions=(
    "You are the architect of a hypothesis-screening loop. Read misses (critic label vs human "
    "label), read the current rules, and call apply_rules_patch with at most "
    f"{MAX_SECTIONS} changed sections so the critic gets those leads right next iteration."))


def _latest_rules():
    return sorted(glob.glob("kit/critic/rules_v*.md"), key=lambda p: int(p.split("_v")[1][:-3]))[-1]


@mcp.tool()
def list_iterations() -> list[dict]:
    """Metrics per completed iteration: kill_precision, false_kill_rate, reason_accuracy, misses."""
    if not os.path.exists("results/metrics.csv"):
        return []
    return list(csv.DictReader(open("results/metrics.csv")))


@mcp.tool()
def get_misses(iteration: int) -> list[dict]:
    """Leads the critic labeled differently from the humans in one iteration, with the true
    table facts. Fields: hypothesis_id, hypothesis_text, human_reason_code, critic_reason_code,
    critic_reason, critic_confidence, table_facts."""
    return json.load(open(f"results/iter{iteration}.json"))["misses"]


@mcp.tool()
def get_rules(version: int | None = None) -> dict:
    """A rules version (default: latest): {version, digest, text}. Sections are '## <reason_code>'.
    Pass the digest to apply_rules_patch as base_rules_digest."""
    path = f"kit/critic/rules_v{version}.md" if version is not None else _latest_rules()
    return {"version": int(path.split("_v")[1][:-3]), "digest": _digest(path), "text": open(path).read()}


@mcp.tool()
def propose_rules_patch(patch: str) -> dict:
    """Dry run: validate a patch against the latest rules without writing. Returns the merged
    text and changed sections, or an error. Call this before apply_rules_patch."""
    try:
        text, changed = render_patch(_latest_rules(), patch)
        return {"ok": True, "changed_sections": changed, "merged_text": text}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_dataset_summary() -> str:
    """The dataset summary the scout used to write the leads (design, top genes, pathways, flags)."""
    return open("data/summaries/OSD-104.md").read()


@mcp.tool()
def apply_rules_patch(patch: str, change_reason: str, base_rules_digest: str,
                      iteration: int, source_run_id: str = "", token: str = "") -> dict:
    """Commit the next rules version. `patch` = blocks of '## <reason_code>' + full replacement
    text (max 2 sections). `base_rules_digest` must equal the digest from get_rules (latest);
    a stale digest is rejected so two conversations cannot race. `iteration` = the iteration
    whose misses motivated the change. Returns {written, version, digest} or {error}."""
    if TOKEN and token != TOKEN:
        return {"error": "invalid token"}
    base = _latest_rules()
    if base_rules_digest != _digest(base):
        return {"error": f"stale base_rules_digest; latest is {os.path.basename(base)} {_digest(base)}"}
    try:
        out = apply_patch(base, patch, change_reason=change_reason, author="aria",
                          extra_meta={"iteration": iteration, "source_run_id": source_run_id,
                                      "base_digest": base_rules_digest, "written_at": time.time()})
        return {"written": out, "version": int(out.split("_v")[1][:-3]), "digest": _digest(out)}
    except ValueError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("HELIX_MCP_HOST", "127.0.0.1"), port=int(os.getenv("HELIX_MCP_PORT", "8765")),
            streamable_http_path="/mcp", json_response=True, stateless_http=True)
