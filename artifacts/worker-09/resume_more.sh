#!/usr/bin/env bash
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
resume() { local name="$1" url="$2" target="$3"
  for i in 1 2 3 4 5 6; do
    timeout 280 curl -sSL -m 270 -C - -A "$UA" -o "$OUT/$name" -w "$name attempt$i: %{http_code} +%{size_download}\n" "$url" || true
    sz=$(wc -c < "$OUT/$name" 2>/dev/null || echo 0); echo "$name size: $sz"
    if [ "$sz" -ge "$target" ]; then echo "$name COMPLETE"; break; fi
  done
}
resume chrusciel1992.pdf "https://www.math.tecnico.ulisboa.pt/~jnatar/nonarxivpapers/Chrusciel.pdf" 13189076
resume full3_2604.04877.html "https://arxiv.org/html/2604.04877v1" 6105891
echo DONE_RESUME
