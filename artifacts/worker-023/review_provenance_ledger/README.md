# W023-F2B-REVIEW-PROVENANCE-01 — content-addressed review-verdict provenance ledger

Worker `worker-023` · node `F2b` · classes `AF-SCC-C0-VAC-GEN` (+ `AF-SCC-C2-VAC-GEN`,
`AF-WCC-VAC-GEN`) · gate of record `G-FORM` · **worker-level measurement only** — no gate
verdict, no node status, no `validation_status`, no canonical write. `reviews/` is read, never
written; all output lives under this directory.

## One-line result

`reviews/*.json` are mutable under fixed names (CF-31). This task delivers a content-addressed,
append-only provenance ledger plus a drift detector that (a) preserves every verdict byte
sequence it has seen, (b) separates **acknowledged supersession** (replacement carries the
replaced sha256 — exit 0) from **silent evidence loss** (no hash-bearing pointer — fail closed),
and (c) recovers the disputed F2b count record: worker-072's withdrawn `accept` is preserved in
the accepted event stream (`#7487f310d208`, received 01:10:14) and is hash-bound in the rev2
replacement, so the flip is **documented, not silent**; only the rev1 bytes are gone.

## Why this exists

- CF-31: the controller's hash-bound scan recorded 4 F2b full accepts at 01:12:39 while the
  formulation lead's census found 0; no reviewer overlap. `astra-life05-verify-gform-r3` must
  publish a per-file binding table at the measured hash before any G-FORM movement.
- worker-036 (`gform_r3_binding_census`, `report.json#3e6122d4154d`) reproduced F1/F2a but not
  F2b and found `reviews/F2b-review-worker-072-rev29.json` rewritten in place at 01:14:54 from
  `accept 4.0` to `revise 3.0`, noting that the accept-bearing bytes are not preserved anywhere
  under `reviews/`. That is a byte-preservation gap, and it is now closed going forward.

## Method (stdlib only, deterministic payloads)

`review_provenance_ledger.py`:

| command | effect |
|---|---|
| `seed` | scan `reviews/*.json`, copy each file's bytes to write-once `store/<sha256>.json`, append an observation to `ledger.jsonl` (path, sha256, size, mtime_ns, verdict fields) |
| `check` | re-scan and classify every path against the latest observation; exit 2 on `REWRITTEN`/`REMOVED` (fail closed) |
| `verify` | re-hash the store: every entry equals its filename digest, every ledger record resolves to hash-equal bytes |
| `diff-manifest` | classify the live corpus against an external pinned `{path: sha256}` manifest (reconstructs an earlier window) |
| `selftest` | 18 synthetic-corpus controls: rewrite / acknowledged supersession / add / remove / touch / restore / store tamper / manifest diff |

Classification: `UNCHANGED` · `TOUCHED` (mtime only) · `SUPERSEDED` (bytes changed, replacement
contains the replaced sha256 as a hex token) · `REWRITTEN` (silent loss) · `RESTORED` (bytes
equal an earlier observation) · `ADDED` · `REMOVED`. `SUPERSEDED`/`RESTORED` are recorded
verdict changes; only `REWRITTEN`/`REMOVED` fail closed. Report payloads carry no wall-clock
fields, so the report bytes are stable for a fixed input set; timestamps live only in the
append-only ledger.

## Measured results (2026-09-12 ~01:20–01:30 +08:00)

Pins: C0 `schemas/af_scc_c0_vacuum.yaml` `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`;
`FROZEN.json` rev29 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`;
worker-036 snapshot manifest `beab69e12028af0305989bbfcf7e0ad1f05b4b724d8e37416bc35e47da8d1766`.

| measurement | value |
|---|---|
| selftest controls | **18/18 pass** (`evidence/selftest.json`) |
| live corpus snapshot | **240 review files**, all `UNCHANGED` after seed, snapshot digest `29833343f9b692c7690a1ee6ee89cb8366223b3b417d7100daef286f5fb16f23` |
| store integrity | **242 byte sequences**, store verify ok, 0 dangling records (`evidence/verify.json`) |
| window delta vs worker-036 snapshot (01:15 → ~01:25) | 190 `UNCHANGED`, 48 `ADDED`, 1 `SUPERSEDED`, **1 `REWRITTEN`** (`evidence/w036_window_delta.json`) |
| fast-mutation demonstration | 1 `ADDED` (`G-FORM-r3-bindings-worker-063.json`) appeared inside a 2-second check pair, caught at the next check |

### F2b / worker-072 case study (the CF-31 flip)

| field | value |
|---|---|
| current file | `reviews/F2b-review-worker-072-rev29.json` `5db91bb0781d…`, verdict `revise`, score 3.0, 2 blocking hard failures |
| `supersedes_sha256` | `7487f310d208367127dd939b9349675e5579619c1e9ec6e8099da8a95720fd36` |
| `supersedes_verdict` / `superseded_at` | `accept` / 2026-09-12T01:14:51+08:00 |
| accepted-stream record | `w072-2026-09-12T01:10:13+08:00-review-f2b`, verdict `accept`, score 4.0, blind true, received 01:10:14, evidence ref `reviews/F2b-review-worker-072-rev29.json#7487f310d208` |
| replacement carries lost hash | **yes** |

Disposition: the accept-bearing **bytes** are not preserved under `reviews/` (worker-036 is
right about bytes), but the **record** survives twice over — the append-only accepted stream and
the rev2 file's own `supersedes_sha256`/`revision_history`. The count is therefore re-derivable
at 4-for-01:12:39 only if the withdrawn accept is excluded by policy; that call belongs to
`astra-life05-verify-gform-r3`, not to this worker. What this instrument guarantees is that from
its seed onward no future flip can lose bytes without a detectable trace.

### A0 window rewrites (same mechanism, live)

Two A0 review files changed bytes inside the 01:15→~01:28 window:

| file | classification | note |
|---|---|---|
| `reviews/A0-review-worker-089.json` | `SUPERSEDED` | replacement contains the replaced sha `9cade89e600c…` |
| `reviews/A0-review-final-verify.json` | `REWRITTEN` | prose says "supersedes … v1 (00:50:20)" but does **not** carry the replaced sha `b5a6cecb2a08…`; a prose pointer is not a hash binding |

That second row is the instrument's point: the same author behaviour that is auditable in one
file is unverifiable in the other, and the detector distinguishes them mechanically.

## Reproduce

Run from the repo root (`/data3/guoshaoyang/workdir/ai4math-swarm`) with the corpus glob kept
relative to that root, so ledger paths stay stable across runs:

```bash
L=artifacts/worker-023/review_provenance_ledger
python3 $L/review_provenance_ledger.py selftest --out $L/evidence/selftest.json
python3 $L/review_provenance_ledger.py seed   --corpus 'reviews/*.json'
python3 $L/review_provenance_ledger.py check  --corpus 'reviews/*.json' --out $L/evidence/check_seed.json
python3 $L/review_provenance_ledger.py verify --out $L/evidence/verify.json
python3 $L/review_provenance_ledger.py diff-manifest --corpus 'reviews/*.json' \
    --manifest artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json \
    --key-mode basename --out $L/evidence/w036_window_delta.json
python3 $L/make_report.py > /dev/null
```

A repeat `check` at unchanged bytes exits 0 with all `UNCHANGED`; `seed` is idempotent for the
store (write-once) and only appends observations. `check` is safe to run at any time — it is the
pass-boundary control: run it immediately before and after every controller pass.

## Limits, non-claims, falsifier

- Preservation starts at seed time; the lost worker-072 **rev1 bytes cannot be recovered**, only
  their identity (`7487f310d208…`) and their verdict record.
- `SUPERSEDED` proves the replacement *names* the replaced hash, not that the replacement's
  content is sound; a deliberate forger can name a hash and still change the verdict.
- The ledger is not a coverage count and not a review verdict; it must never be counted toward
  G-FORM coverage.
- English/JSON field heuristics only; a verdict alias the extractor does not know is recorded as
  absent, never guessed.
- Not a gate verdict, not a node completion, not a canonical instrument, not a claim about
  C0/C2 physics.
- **Falsified if** the detector fails to flag a synthetic silent `accept -> revise` rewrite at
  the same path (selftest control); it flags an unchanged or merely touched file; `verify` finds
  a store entry whose bytes differ from its filename digest or a dangling ledger record; the
  w036 window delta is not reproducible from
  `artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json#beab69e12028`; or
  `reviews/F2b-review-worker-072-rev29.json` stops containing the accepted stream's recorded
  prefix `7487f310d208`.
