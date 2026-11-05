#!/usr/bin/env bash
# Fetch the external COBOL test corpus at the commits pinned in corpus/manifest.json.
# The repositories are test inputs only and are never committed (corpus/repos/ is git-ignored).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${PHOENIX_CORPUS_DIR:-$ROOT/corpus/repos}"
mkdir -p "$DEST"
python3 - "$ROOT/corpus/manifest.json" <<'PY' | while read -r url sha dir; do
import json, sys
for r in json.load(open(sys.argv[1]))["repositories"]:
    print(r["url"], r["commit"], r["dir"])
PY
  target="$DEST/$dir"
  if [ ! -d "$target/.git" ]; then
    git clone --quiet --filter=blob:none "$url" "$target"
  fi
  git -C "$target" fetch --quiet origin "$sha" 2>/dev/null || true
  git -C "$target" checkout --quiet "$sha"
  echo "corpus: $dir @ $(git -C "$target" rev-parse --short HEAD)"
done
