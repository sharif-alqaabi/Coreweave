"""Helix MCP server: the tools ARIA (or any MCP client) can call to act as the architect.

    python3 helix/mcp_server.py                 # serves http://0.0.0.0:8765/mcp
    cloudflared tunnel --url http://localhost:8765   # public URL to paste into ARIA

Tools: list_iterations, get_misses, get_rules, get_dataset_summary, apply_rules_patch.
apply_rules_patch is the wire: ARIA writes rules_v{n+1}.md; loop.py picks it up.
"""
import csv, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.mcpserver import MCPServer
from helix.reflect import apply_patch, MAX_SECTIONS

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
def get_rules(version: int | None = None) -> str:
    """Full text of a rules version (default: latest). Sections are '## <reason_code>'."""
    path = f"kit/critic/rules_v{version}.md" if version is not None else _latest_rules()
    return open(path).read()


@mcp.tool()
def get_dataset_summary() -> str:
    """The dataset summary the scout used to write the leads (design, top genes, pathways, flags)."""
    return open("data/summaries/OSD-104.md").read()


@mcp.tool()
def apply_rules_patch(patch: str, change_reason: str) -> dict:
    """Write the next rules version. `patch` = one or more blocks of '## <reason_code>' followed
    by the full replacement text for that section (max 2 sections). Returns the new file path
    and its text, or an error explaining why the patch was rejected."""
    try:
        out = apply_patch(_latest_rules(), patch, change_reason=change_reason, author="aria")
        return {"written": out, "rules": open(out).read()}
    except ValueError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("HELIX_MCP_HOST", "127.0.0.1"), port=int(os.getenv("HELIX_MCP_PORT", "8765")),
            streamable_http_path="/mcp", json_response=True, stateless_http=True)
