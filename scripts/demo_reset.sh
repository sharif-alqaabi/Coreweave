#!/usr/bin/env bash
# Put the repo in "iteration 0" state for a live run. Archives current rules versions,
# results and patches under runs/<timestamp>/ so nothing is lost.
set -e
cd "$(dirname "$0")/.."
stamp=$(date +%Y%m%d-%H%M%S); dest="runs/$stamp"; mkdir -p "$dest"
shopt -s nullglob
for f in kit/critic/rules_v[1-9]*.md kit/critic/rules_v[1-9]*.meta.json; do mv "$f" "$dest/"; done
[ -d results ] && [ "$(ls -A results)" ] && mv results "$dest/results" || true
mkdir -p results
ls patches/iter*.md >/dev/null 2>&1 && mkdir -p "$dest/patches" && mv patches/iter*.md "$dest/patches/" || true
echo "reset to rules_v0; previous run archived in $dest"
ls kit/critic
