"""
Heterogeneous proposer pool over MASO's configured providers.

Adapted from swarm-work/data/gen1/swarm_launcher.py, with three changes that the measurements
on 2026-09-10 forced:

  * gen1 launched MASO *agent sessions* (tool-using, stateful). For search we want stateless
    chat completions: an agent session per proposal would spin up a whole tool loop for a
    single function body, and the decisive experiment showed the LLM's per-call proposal is
    what matters, not its ability to poke around. So this talks to the provider endpoints
    directly, the way gen1's launcher talked to the session API.
  * Per-family accounting is mandatory, not optional. Mixing a weaker family in cost me on
    every axis in the LLM run (valid 27/40 vs 31/40). A pool that cannot tell you which
    family is paying for itself will silently dilute.
  * reasoning_effort must be set explicitly. gpt-5.6-sol with no effort setting burns the whole
    completion budget on hidden reasoning and returns EMPTY content -- 36 calls produced
    25212 completion tokens and zero usable output before this was found.
"""
from __future__ import annotations
import re, json, time, threading, urllib.request, random

CFG_PATH = '/Users/bytedance/.maso/model-providers.yaml'
# families that are actually distinct lineages, not the same base with a different label
DEFAULT_FAMILIES = ('sol', 'qwenmax', 'o50')


def load_providers(names=DEFAULT_FAMILIES) -> dict[str, dict]:
    cfg = open(CFG_PATH).read()
    out = {}
    for n in names:
        m = re.search(rf'\n  {n}:\n(.*?)(?=\n  [a-z0-9_-]+:\n|\Z)', cfg, re.S)
        if not m:
            continue
        b = m.group(1)
        try:
            out[n] = dict(base=re.search(r'base_url:\s*(\S+)', b).group(1),
                          key=re.search(r'api_key:\s*(\S+)', b).group(1).strip('"\''),
                          model=re.search(r'model:\s*(\S+)', b).group(1),
                          header=(re.search(r'x-source:\s*(\S+)', b).group(1)
                                  if 'x-source' in b else None))
        except AttributeError:
            continue
    return out


class Pool:
    def __init__(self, families=DEFAULT_FAMILIES, concurrency=6, effort='low',
                 max_tokens=3000, timeout=180):
        self.providers = load_providers(families)
        if not self.providers:
            raise RuntimeError('no usable providers in ' + CFG_PATH)
        self.names = list(self.providers)
        self.sem = threading.Semaphore(concurrency)
        self.effort, self.max_tokens, self.timeout = effort, max_tokens, timeout
        self.usage = {n: dict(calls=0, prompt=0, completion=0, fail=0, empty=0)
                      for n in self.names}
        self.lock = threading.Lock()

    def probe(self) -> dict[str, str]:
        """Which families actually answer right now. Providers die independently
        (gemini 429'd, OpenRouter free tier down to one model) so this must be checked
        at start, not assumed from the config."""
        out = {}
        for n in self.names:
            try:
                t = self.chat(n, [{"role": "user", "content": "Reply with exactly: ok"}],
                              max_tokens=32)
                out[n] = 'ok' if t.strip() else 'EMPTY'
            except Exception as e:
                out[n] = f'FAIL {type(e).__name__}'
        return out

    def chat(self, family, messages, max_tokens=None, retries=3) -> str:
        pv = self.providers[family]
        body = dict(model=pv['model'], messages=messages,
                    max_tokens=max_tokens or self.max_tokens)
        if self.effort:
            body['reasoning_effort'] = self.effort
        data = json.dumps(body).encode()
        headers = {"content-type": "application/json",
                   "authorization": f"Bearer {pv['key']}"}
        if pv.get('header'):
            headers['x-source'] = pv['header']
        with self.sem:
            for attempt in range(retries):
                try:
                    req = urllib.request.Request(pv['base'] + "/chat/completions",
                                                 data=data, headers=headers)
                    d = json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
                    msg = d["choices"][0]["message"]
                    txt = msg.get("content") or ""
                    u = d.get("usage") or {}
                    with self.lock:
                        s = self.usage[family]
                        s['calls'] += 1
                        s['prompt'] += u.get('prompt_tokens', 0)
                        s['completion'] += u.get('completion_tokens', 0)
                        if not txt.strip():
                            s['empty'] += 1
                    return txt
                except Exception:
                    if attempt == retries - 1:
                        with self.lock:
                            self.usage[family]['fail'] += 1
                        return ""
                    time.sleep(2 * (attempt + 1))
        return ""

    def pick(self, rng: random.Random, live: list[str] | None = None) -> str:
        return rng.choice(live or self.names)

    def report(self) -> dict:
        with self.lock:
            return {k: dict(v) for k, v in self.usage.items()}
