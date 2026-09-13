"""Enrich leads with true numbers from the table, and build the one-judgment
payload the critic (Jev or Claude) sees.

    enrich(leads, table)          -> adds lead["table_facts"] (pandas, never the LLM)
    build_payload(lead, table)    -> dict for one critic call
"""
import glob, json
from helix.summarize import load, significant, header, sample_flags, go_term_facts

OPTIONS = ["ok", "already_known", "underpowered", "confound",
           "contradicted", "untestable", "no_mechanism"]


class Table:
    """Load the CSV once; answer gene / GO-term lookups many times."""
    def __init__(self, path, alpha=0.05):
        self.df, self.lfc, self.padj, self.a, self.b, self.grp = load(path)
        self.sig = significant(self.df, self.padj, alpha)
        self.header = "\n".join(header(path.split("/")[-1], self.df, self.sig,
                                       self.lfc, self.a, self.b, self.grp, alpha))
        self.flags = "; ".join(sample_flags(self.sig, self.lfc, self.grp, self.a, self.b))

    def facts(self, key):
        if key.startswith("GO:"):
            return go_term_facts(self.df, self.sig, self.lfc, key)
        hits = self.df[self.df["SYMBOL"] == key]          # symbols can repeat (isoforms):
        if hits.empty:                                     # take the most significant row
            return {"error": "not in table"}
        r = hits.sort_values(self.padj, na_position="last").iloc[0]
        hi = self.a if r[self.lfc] > 0 else self.b
        carriers = [c.split("_")[-1] for c in self.grp[hi] if r[c] > 1]
        return {"log2fc": round(float(r[self.lfc]), 2), "padj": float(r[self.padj]),
                "higher_group": hi, "carriers": f"{len(carriers)}/{len(self.grp[hi])}",
                "carrier_samples": carriers,
                "mean_count": {g: round(float(r[self.grp[g]].mean())) for g in (self.a, self.b)}}


def enrich(leads, table):
    """Look up every cited gene / GO id once and store the truth on the lead."""
    for lead in leads:
        keys = lead.get("rows") or [k for ev in lead.get("evidence", []) for k in ev.get("rows", [])]
        lead["table_facts"] = {k: table.facts(k) for k in keys}
    return leads


def build_payload(lead, table, rules_dir="kit/critic", rules_file=None):
    paths = [f"{rules_dir}/{rules_file}"] if rules_file else sorted(glob.glob(f"{rules_dir}/*.md"))[-1:]
    rules = "\n\n".join(open(p).read() for p in paths)
    facts = lead.get("table_facts") or enrich([lead], table)[0]["table_facts"]
    return {"input": {"claim": lead["claim"],
                      "why_not_known": lead.get("why_not_known", ""),
                      "next_step": lead.get("next_step", ""),
                      "table_facts": facts,
                      "dataset": table.header,
                      "sample_flags": table.flags,
                      "rules": rules},
            "options": OPTIONS}


if __name__ == "__main__":                       # python3 -m helix.critic_payload leads.json table.csv
    import sys
    leads = json.load(open(sys.argv[1]))
    out = enrich(leads, Table(sys.argv[2]))
    json.dump(out, open(sys.argv[1].replace(".json", "_enriched.json"), "w"), indent=1)
