#!/usr/bin/env bash
# Worker 09 L1 P2: second fetch batch (SCC-side ledger sources lacking theorem text).
# Same conventions as fetch_sources.sh: raw files + status + sha256 into sources/.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MANIFEST="$OUT/fetch_manifest_p2.tsv"
: > "$MANIFEST"

fetch() {
  local name="$1" url="$2" dest="$OUT/$1" code size sha
  code=$(curl -sSL -m 90 --retry 2 -A "$UA" -o "$dest" -w '%{http_code}' "$url" 2>"$OUT/.$1.err") || code="ERR"
  if [ -f "$dest" ]; then size=$(wc -c <"$dest"); sha=$(sha256sum "$dest" | cut -d' ' -f1); else size=0; sha="-"; fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$code" "$size" "$sha" "$url" >> "$MANIFEST"
  printf '%-30s %s %9s %s\n' "$name" "$code" "$size" "${sha:0:16}"
}

# metadata
fetch abs_2001.11156.html  https://arxiv.org/abs/2001.11156
fetch abs_1702.05715.html  https://arxiv.org/abs/1702.05715
fetch abs_1702.05716.html  https://arxiv.org/abs/1702.05716
fetch abs_2007.12049.html  https://arxiv.org/abs/2007.12049
fetch abs_1311.4970.html   https://arxiv.org/abs/1311.4970
fetch abs_2309.14420.html  https://arxiv.org/abs/2309.14420
fetch abs_2201.12294.html  https://arxiv.org/abs/2201.12294

# full text: try arXiv HTML, fall back to ar5iv if the result is a stub (<60 KB)
for pair in "2001.11156v2 full2_2001.11156.html" "1702.05715v2 full2_1702.05715.html" \
            "1702.05716v2 full2_1702.05716.html" "2007.12049v2 full2_2007.12049.html" \
            "2309.14420v2 full2_2309.14420.html" "2201.12294v2 full2_2201.12294.html"; do
  set -- $pair
  fetch "$2" "https://arxiv.org/html/$1"
  sz=$(wc -c <"$OUT/$2" 2>/dev/null || echo 0)
  if [ "$sz" -lt 60000 ]; then
    fetch "$2" "https://ar5iv.labs.arxiv.org/html/${1%v*}"
  fi
done
# 1311.4970 is pre-2015: ar5iv only
fetch full2_1311.4970.html https://ar5iv.labs.arxiv.org/html/1311.4970
echo "--- p2 manifest ---"
cat "$MANIFEST"
