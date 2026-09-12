#!/usr/bin/env bash
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
for i in 1 2 3 4 5 6 7 8; do
  timeout 280 curl -sSL -m 270 -C - -A "$UA" -o "$OUT/chrusciel1992.pdf" -w "attempt$i: %{http_code} +%{size_download} total=%{size_upload}\n" "https://www.math.tecnico.ulisboa.pt/~jnatar/nonarxivpapers/Chrusciel.pdf" || true
  sz=$(wc -c < "$OUT/chrusciel1992.pdf" 2>/dev/null || echo 0)
  echo "size now: $sz"
  if [ "$sz" -ge 13189076 ]; then echo COMPLETE; break; fi
done
echo DONE_CHRUSCIEL
