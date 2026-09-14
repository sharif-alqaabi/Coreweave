"""Field-wide lookups across every differential-expression table on disk with DuckDB: one SQL query over the CSVs in
place, no loading into pandas. Used for "where else does this gene move?" questions at the scale of the whole catalog.

    python -m helix.tables Drd4 Pfkfb3            # every table, direction, padj
    from helix.tables import across_field; across_field(["Drd4"])
"""
from __future__ import annotations
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helix.settings import ROOT

RAW = os.path.join(ROOT, "data/raw")


def _contrast_columns(con, path):
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path}', sample_size=200)").fetchall()]
    lfcs = [c for c in cols if c.startswith("Log2fc_(")]
    if not lfcs:
        return None, None
    from helix.summarize import pick_contrast
    lfc = pick_contrast(lfcs)
    return lfc, "Adj.p.value_" + lfc[len("Log2fc_"):]


def across_field(symbols, alpha=0.05):
    """[{symbol, dataset, log2fc, padj, direction}] for each symbol in each table; direction is +1/-1 when padj < alpha, 0 otherwise."""
    import duckdb
    con = duckdb.connect()
    out = []
    syms = ", ".join("'" + s.replace("'", "''") + "'" for s in symbols)
    for path in sorted(glob.glob(os.path.join(RAW, "OSD-*.csv"))):
        lfc, padj = _contrast_columns(con, path)
        if not lfc:
            continue
        ds = os.path.basename(path).split("_")[0]
        rows = con.execute(f'SELECT "SYMBOL", "{lfc}", "{padj}" FROM read_csv_auto(\'{path}\', sample_size=200, ignore_errors=true) '
                           f'WHERE "SYMBOL" IN ({syms}) ORDER BY "{padj}" NULLS LAST').fetchall()
        seen = set()
        for sym, l, p in rows:
            if sym in seen:                                     # isoforms repeat a symbol: keep the most significant
                continue
            seen.add(sym)
            try:
                l, p = float(l), float(p)
            except (TypeError, ValueError):
                continue
            out.append({"symbol": sym, "dataset": ds, "log2fc": round(l, 2), "padj": p,
                        "direction": (1 if l > 0 else -1) if p == p and p < alpha else 0})
    return out


if __name__ == "__main__":
    import time
    t = time.time()
    for r in across_field(sys.argv[1:] or ["Drd4"]):
        print(f"{r['symbol']:10} {r['dataset']:8} log2fc {r['log2fc']:+6.2f}  padj {r['padj']:.2g}  {'up' if r['direction'] > 0 else 'down' if r['direction'] < 0 else 'n.s.'}")
    print(f"({time.time()-t:.1f} s over {len(glob.glob(os.path.join(RAW, 'OSD-*.csv')))} tables)")
