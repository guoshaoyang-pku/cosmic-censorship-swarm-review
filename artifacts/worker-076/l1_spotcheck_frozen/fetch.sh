#!/usr/bin/env bash
# worker-076 independent re-fetch spot check, frozen L1 hash 315c19145065...
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/raw"
UA='Mozilla/5.0 (X11; Linux x86_64) worker-076-spotcheck/1.0 (research verification)'
fetch(){ # name url
  local name="$1" url="$2"
  local code
  code=$(curl -sS -L --max-time 60 -A "$UA" -H 'Accept: application/json, application/atom+xml, text/html;q=0.9' \
        -D "$OUT/$name.headers" -o "$OUT/$name.body" -w '%{http_code}' "$url" 2>"$OUT/$name.curl.err")
  echo "$code" > "$OUT/$name.status"
  printf '%s\t%s\t%s\n' "$name" "$code" "$url" >> "$OUT/fetch_index.tsv"
}
fetch src035_crossref 'https://api.crossref.org/works/10.4310/acta.2018.v220.n1.a1'
fetch src035_inspire  'https://inspirehep.net/api/literature/1469117'
fetch src040_arxiv     'https://export.arxiv.org/api/query?id_list=2205.14808'
fetch src047_arxiv     'https://export.arxiv.org/api/query?id_list=2603.17911'
fetch src056_arxiv     'https://export.arxiv.org/api/query?id_list=gr-qc/0307013'
fetch src078_arxiv     'https://export.arxiv.org/api/query?id_list=2606.28253'
fetch src080_arxiv     'https://export.arxiv.org/api/query?id_list=2604.04877'
sha256sum "$OUT"/*.body > "$OUT/fetched_sha256.txt"
cat "$OUT/fetch_index.tsv"
