#!/bin/bash
# Live training for the demo video: one real round from the hand-written rules_v0 on a 60-lead slice (the two harder studies),
# inside a throwaway copy of the repo (a git worktree), so nothing in the real kit/ or results/ changes.
#
#   bash scripts/live_train.sh            # ~5-6 min incl. up to a 4-minute window for ARIA; prints misses, tournament, v0 -> v1 diff
#
# Watch it in three places at once: this terminal, the W&B run it logs (group "video"), and the
# dashboard pointed at the copy:  cd $LIVE && marimo run app/dashboard.py -p 2722
set -e
LIVE=${LIVE:-/tmp/helix-live}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
rm -rf "$LIVE"; git -C "$ROOT" worktree prune; git -C "$ROOT" worktree add -q --detach "$LIVE" HEAD
cp "$ROOT/.env" "$LIVE/.env"
cd "$LIVE"
find kit/critic -name 'rules_v*' ! -name 'rules_v0.md' -delete          # start from the seed
rm -rf results patches/*.md; mkdir -p results                            # no history, no canned patches
python3 - <<'PY'
import json
leads = [l for l in json.load(open("data/golden/train_llm_only.json")) if l["dataset"] in ("OSD-104", "OSD-467")]
json.dump(leads, open("data/golden/train_video.json", "w"), indent=1)
from collections import Counter; print(f"training slice: {len(leads)} leads from OSD-104 (soleus) and OSD-467 (bone),", dict(Counter(l['label'] for l in leads)))
PY
echo "=== round 0: critic judges with rules_v0, misses go to three architects, tournament, promotion ==="
python3 -u loop.py --iterations 1 --train data/golden/train_video.json --table data/raw/OSD-104_rna_seq_differential_expression.csv data/raw/OSD-467_differential_expression.csv \
    --group video --wait-for-aria ${ARIA_WAIT:-240} 2>&1 | grep --line-buffered -v "🍩\|warnings.warn\|RequestsDependency\|Traces will not be logged\|subsequent messages"
echo; echo "=== what changed: rules_v0 -> rules_v1 ==="
diff <(cat kit/critic/rules_v0.md) <(cat kit/critic/rules_v1.md) | cut -c1-200 || true
echo; echo "copy lives at $LIVE (dashboard: cd $LIVE && marimo run app/dashboard.py -p 2722)"
