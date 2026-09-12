#!/usr/bin/env bash
# Worker 09 (deepseek-flash-09) P5: class-bound L1 adjudication of the two lead-formulation
# quarantined pointers for AF-SCC-C0-VAC-GEN:
#   (1) Grant-Kunzinger-Saemann-Steinbauer, "The future is not always open", arXiv:1901.07996
#       (cited in the C0 extension_predicate clause (f) convention caveat, marked UNVERIFIED)
#   (2) Rendall, "The nature of spacetime singularities", arXiv:gr-qc/0503112
#       (cited for extendible maximal Cauchy developments / Cauchy horizons, Taub-NUT, Kerr/RN)
# Fetches abs + full text + Crossref/openalex records into artifacts/worker-09/sources/.
# Read-only with respect to every other path. Unresolved is a valid output.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/sources"
mkdir -p "$OUT"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MANIFEST="$OUT/fetch_manifest_p5.tsv"
: > "$MANIFEST"

fetch() {  # fetch <name> <url>
  local name="$1" url="$2" dest="$OUT/$1" code size sha
  code=$(curl -sSL -m 120 --retry 2 -A "$UA" -o "$dest" -w '%{http_code}' "$url" 2>"$OUT/.$name.err") || code="ERR"
  if [ -f "$dest" ]; then size=$(wc -c <"$dest"); sha=$(sha256sum "$dest" | cut -d' ' -f1); else size=0; sha="-"; fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$code" "$size" "$sha" "$url" >> "$MANIFEST"
  printf '%-38s %s %8s %s\n' "$name" "$code" "$size" "${sha:0:16}"
}

# --- pointer 1: Grant et al. 1901.07996 (published: Lett. Math. Phys. 109, 83-91 (2019)) ---
fetch abs_1901.07996.html    https://arxiv.org/abs/1901.07996
fetch full5_1901.07996.html  https://ar5iv.labs.arxiv.org/html/1901.07996
fetch crossref_1901_07996.json https://api.crossref.org/works/10.1007/s11005-018-1110-z

# --- pointer 2: Rendall gr-qc/0503112 ---
fetch abs_grqc0503112.html   https://arxiv.org/abs/gr-qc/0503112
fetch full5_grqc0503112.html https://ar5iv.labs.arxiv.org/html/gr-qc/0503112
fetch crossref_grqc0503112.json https://api.crossref.org/works?query.bibliographic=Rendall+nature+of+spacetime+singularities&rows=3
