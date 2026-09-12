#!/usr/bin/env bash
# Worker 09 (deepseek-flash-09) L1 source fetcher.
# Assignment asg-2026-09-11-L1-deepseek-flash-09-18: web-verify SCC-side citations,
# distinguish C0 from C2 explicitly, record resolver results, unresolved is valid output.
# Fetches ABS metadata, full-text HTML (where available) and OpenAlex records into
# artifacts/worker-09/sources/, with HTTP status + sha256 recorded. No writes outside
# artifacts/worker-09/.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/sources"
mkdir -p "$OUT"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MANIFEST="$OUT/fetch_manifest.tsv"
: > "$MANIFEST"

fetch() {  # fetch <name> <url>
  local name="$1" url="$2" dest="$OUT/$1" code size sha
  code=$(curl -sSL -m 90 --retry 2 -A "$UA" -o "$dest" -w '%{http_code}' "$url" 2>"$OUT/.$1.err") || code="ERR"
  if [ -f "$dest" ]; then size=$(wc -c <"$dest"); sha=$(sha256sum "$dest" | cut -d' ' -f1); else size=0; sha="-"; fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$code" "$size" "$sha" "$url" >> "$MANIFEST"
  printf '%-34s %s %8s %s\n' "$name" "$code" "$size" "${sha:0:16}"
}

# --- abs metadata (arXiv) ---
fetch abs_1501.04598.html   https://arxiv.org/abs/1501.04598
fetch abs_1710.01722.html   https://arxiv.org/abs/1710.01722
fetch abs_1704.05790.html   https://arxiv.org/abs/1704.05790
fetch abs_1406.7261.html    https://arxiv.org/abs/1406.7261
fetch abs_1507.00601.html   https://arxiv.org/abs/1507.00601
fetch abs_0711.4620.html    https://arxiv.org/abs/0711.4620
fetch abs_grqc0307013.html  https://arxiv.org/abs/gr-qc/0307013
fetch abs_grqc9712084.html  https://arxiv.org/abs/gr-qc/9712084

# --- full text (arXiv HTML experimental, else ar5iv) ---
fetch full_1501.04598.html  https://arxiv.org/html/1501.04598v1
fetch full_1704.05790.html  https://arxiv.org/html/1704.05790v3
fetch full_1406.7261.html   https://arxiv.org/html/1406.7261v4
fetch full_1507.00601.html  https://arxiv.org/html/1507.00601v2
fetch full_0711.4620.html   https://arxiv.org/html/0711.4620v1
fetch full_grqc0307013.html https://ar5iv.labs.arxiv.org/html/gr-qc/0307013
fetch full_1710.01722.html  https://ar5iv.labs.arxiv.org/html/1710.01722

# --- publisher / database records ---
fetch annals_dafermos2003.pdf https://annals.math.princeton.edu/wp-content/uploads/annals-v158-n3-p03.pdf
fetch openalex_dafermos2003.json "https://api.openalex.org/works/doi:10.4007/annals.2003.158.875"
fetch openalex_dafermos2005.json "https://api.openalex.org/works/doi:10.1002/cpa.20071"
fetch openalex_choptuik1993.json "https://api.openalex.org/works/doi:10.1103/PhysRevLett.70.9"
fetch openalex_gmg2007.json     "https://api.openalex.org/works/doi:10.12942/lrr-2007-5"
fetch openalex_lukoh2017.json   "https://api.openalex.org/works/doi:10.1215/00127094-3715189"
fetch openalex_cgns2017.json    "https://api.openalex.org/works/doi:10.1007/s40818-017-0028-6"
fetch openalex_vdm2018.json     "https://api.openalex.org/works/doi:10.1007/s00220-017-3079-3"
fetch openalex_dl2025.json      "https://api.openalex.org/works/doi:10.4007/annals.2025.202.2.1"
fetch openalex_sbierski2018.json "https://api.openalex.org/works/doi:10.4310/jdg/1519959623"
echo "--- manifest ---"
cat "$MANIFEST"
