# W027-GNUM-C8-KEYBIND-01 — G-NUM criterion C8 reports "unbound" while an eligible accept binds the measured protocol

Class-bound: `AF-WCC-SCALAR-SPH` · node `N0` · gate `G-NUM` · actor `worker-027` · run 2026-09-12T00:27+08:00

## Question

At the pinned snapshot the controller's G-NUM gate reason says:

> "protocol measured 1e6cdf04d7a2; the recorded protocol verdict
> reviews/G-NUM-protocol-review.json binds **unbound (stale)**, so criterion C8 is the
> exact unmet requirement."

At the same snapshot `reviews/G-NUM-protocol-review.json` is `verdict=accept`,
`counts_as_full_schema_verdict=true`, `reviewer=astra-lead-audit`, and declares
`reviewed_sha256 = 1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` — exactly the
measured sha256 of `numerics/CONVERGENCE_PROTOCOL.md`. Is C8 actually unsatisfied, or is the
reason an artifact of how it is read?

## Result — `FINDING_REPRODUCED` (12/12 registered checks and controls hold)

**W027-F1 (major, confirmed).** The G-NUM reason's own reader extracts only the key
`artifact_sha256`:

`research_map/astra_lifecycle.py:259` (pinned sha `d7a65651250e…`):
```python
proto_rev_h = str(json.loads(proto_review.read_text()).get("artifact_sha256") or "unbound")[:12]
```

The verdict stores its pin under `reviewed_sha256`, so the reader returns `"unbound"`. The
review is an eligible full-schema accept bound to the current revision; the "stale" wording is a
key-scope mismatch, not a content finding.

**W027-F2 (major, confirmed).** The corpus-wide scanner cannot compensate.
`review_coverage()` binds pins from `artifact_sha256 / reviewed_sha256 / sha256 / cited_sha256`
(`astra_lifecycle.py:147`, prefix rule `:185`) but iterates only the measured node-id universe
`{A0, A1, A2, F0, F1, F2a, F2b, L0, L1, N0, N1, N1-BLOCK}` (`:119-141`); the review's
`target_id` is `G-NUM-protocol`, which is not in that universe or in `TARGET_ALIASES`. No
`gate_audit` path therefore counts the verdict, whatever key it uses.

**W027-F3 (info, census).** Single-key `artifact_sha256` reads also exist at
`astra_lifecycle.py:94` (map declared-hash path, where the key is correct) and in
`artifacts/audit/*.py`; the both-keys convention lives only in `_explicit_pins`.

## Evidence (all hashed at run time)

| role | path | sha256 |
|---|---|---|
| protocol | `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2…` |
| review | `reviews/G-NUM-protocol-review.json` | `8137f18f1a3b…` |
| controller tool | `research_map/astra_lifecycle.py` | `d7a65651250e…` |
| newest lifecycle | `runtime/state/controller_verification/lifecycle_20260912-002440.json` | `d33af1f9653a…` |
| map (carries the reason) | `research_map/research_map.json` | `4fd40d4d1e4f…` |

Byte snapshots of all four inputs are in `snapshots/` (`byte_identical: true` for each).

## Controls

- `CTRL-C1` synthetic review with only `artifact_sha256` → expression returns `1e6cdf04d7a2`
  (reader is sensitive; not type-broken).
- `CTRL-C2` synthetic review with only `reviewed_sha256` → expression returns `unbound`
  (defect reproduced without the real file).
- `CTRL-C3` one-nibble-mutated hash → does not bind (not a rubber stamp).
- `CTRL-C4` same pin, verdict `revise` → binds by hash but is not in the accept set.
- `CTRL-C5` empty object → `unbound`.
- Drift control: `--expect-protocol 000…0` exits `2 INPUT_DRIFT` fail-closed.

## Falsifier

Re-run `check_c8_binding.py` at the pinned hashes:

```bash
python3 artifacts/worker-027/g_num_c8_keybind/check_c8_binding.py \
  --expect-protocol 1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274 \
  --expect-review   8137f18f1a3b2b01580e1874262e546048bd681672c1b7699e6d784842307017 \
  --expect-controller d7a65651250ea9d8cee8ab6f6715a005ef4e7e1b63112991e6efe426d2d72377
```

Falsified if the review's `reviewed_sha256` ≠ measured protocol hash, or the review is not an
accept, or check `C3` returns the protocol prefix, or the newest lifecycle G-NUM reason no longer
contains `binds unbound (stale)`. Exit `0` = finding reproduced, `3` = falsified, `2` = input drift.

## Non-claims

No gate verdict, no node completion, no edit to any canonical artifact, review, map, or
controller tool; no adjudication of the protocol's numerical content, `N0` convergence, or the
scientific merit of the review. The review file is the audit lead's artifact and is cited, not
modified.
