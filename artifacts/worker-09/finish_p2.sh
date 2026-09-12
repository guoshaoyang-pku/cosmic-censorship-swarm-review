#!/usr/bin/env bash
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
get() { local name="$1" url="$2"; timeout 500 curl -sSL -m 480 --retry 1 -A "$UA" -o "$OUT/$name" -w "$name code:%{http_code} size:%{size_download}\n" "$url" || echo "$name FAILED"; }
get full2_1702.05716.html https://arxiv.org/html/1702.05716v2
get full2_2309.14420.html https://arxiv.org/html/2309.14420v2
get full2_1311.4970.html  https://ar5iv.labs.arxiv.org/html/1311.4970
get full2_2201.12294.html https://arxiv.org/html/2201.12294v2
echo DONE_P2_FETCH
