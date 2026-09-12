#!/usr/bin/env bash
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
g(){ local n="$1" u="$2"; timeout 280 curl -sSL -m 270 --retry 1 -A "$UA" -o "$OUT/$n" -w "$n %{http_code} %{size_download}\n" "$u" || echo "$n FAILED"; }
g full4_1311.4970.html  https://ar5iv.labs.arxiv.org/html/1311.4970
g full4_2511.13422.html https://arxiv.org/html/2511.13422v2
g full4_1512.08259.html https://ar5iv.labs.arxiv.org/html/1512.08259
echo DONE_P6
