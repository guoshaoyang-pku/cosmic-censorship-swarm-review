#!/usr/bin/env bash
set -u
OUT="$(cd "$(dirname "$0")" && pwd)/sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
g() { local name="$1" url="$2"; timeout 240 curl -sSL -m 220 --retry 1 -A "$UA" -o "$OUT/$name" -w "$name %{http_code} %{size_download}\n" "$url" || echo "$name FAILED"; }
g abs_2606.28253.html https://arxiv.org/abs/2606.28253
g abs_2604.04877.html https://arxiv.org/abs/2604.04877
g abs_2409.18838.html https://arxiv.org/abs/2409.18838
g abs_2604.06283.html https://arxiv.org/abs/2604.06283
g abs_2503.24114.html https://arxiv.org/abs/2503.24114
g full3_2604.04877.html https://arxiv.org/html/2604.04877v1
g full3_2409.18838.html https://arxiv.org/html/2409.18838v2
echo DONE_P3_FETCH
