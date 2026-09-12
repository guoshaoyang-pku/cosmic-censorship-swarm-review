# W070-GFORM-REV29-PINBIND-01 — per-file pin-binding census of FROZEN rev29

**Actor:** worker-070 · **Gate:** G-FORM (pending; this is evidence, not a verdict) ·
**Node/classes:** F1/F2a/F2b · AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN ·
**Object under test:** `artifacts/formulation/FROZEN.json`
sha256 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
(rev 29, frozen_at 2026-09-12T00:57:26+08:00), stable start and end of run.

No inbox card existed for worker-070. One bounded class-bound task was self-taken from the
open G-FORM item named by `astra-life05-verify-gform-r3`: *FROZEN/per-file pin binding*.
The prior landing audits measured the superseded FROZEN revisions (`2f358f6722d9`,
`3d9e3d77`); this census is at the live rev29 bytes.

## Result — `verdict: BINDING_GAPS`

| leg | result |
|---|---|
| 52 declared pins (50 `files` + 2 `logical_artifacts`) at their declared paths | **52/52 MATCH** |
| three schema mirror pairs (canonical vs `artifacts/formulation/schemas/`) | 3/3 byte-identical |
| companion pair (declared taxonomy vs class-contract supplement) | distinct, as `path_policy` requires |
| FROZEN drift during run | none |
| controls (known-good, one-byte mutation, synthetic missing, hash-index positive, no self-reference, stream extraction, no drift) | 7/7 pass |
| accepted-stream leg (latest artifact event per canonical path) | **2 disagreements** |

Disk-side per-file binding is clean. The two gaps are in the *accepted stream*:

1. **`schemas/af_scc_c0_vacuum.yaml` (F2b)** — the latest artifact event by authored
   `created_at` is `w06-20260912T0115-f2b-rev6` (deepseek-flash-06, 01:15:00), declaring
   `e6b1af2bd692…` — 17 minutes *after* the FROZEN rev29 freeze (00:57:26) and after the
   canonical publication event `lead-form-20260912T005743-02` (00:57:43, `b2ab6acb2bbe…`).
   The `e6b1af2b…` bytes are not on disk in any scanned root. FROZEN, disk, registry and the
   controller's measured pin all agree on `b2ab6acb2bbe…`. Classified
   `POST_FREEZE_STALE_PIN_CLAIM_ON_FROZEN_CANONICAL_PATH`.

2. **`research_map/formulation_taxonomy.yaml` (F0)** — the latest artifact event by authored
   `created_at` is `leadform-artifact-0095-r4f0` (authored 00:44:00, ingested 00:20:09),
   declaring superseded rev4 `276009f4f63d…`, while disk/FROZEN/registry are rev5
   `0abb9ed8a961…` (published 00:35:52). Authored-time order and arrival order disagree.
   Classified `SUPERSEDED_HASH_IS_LATEST_BY_AUTHORED_TIMESTAMP`.

Both gaps are recorded, not repaired and not adjudicated — the controller / astra-lead-audit
owns that. They change what a *safe binding rule* is: the authoritative per-file pin must be
the measured FROZEN/disk/registry hash; the event stream is publication history and must be
checked for post-freeze claims rather than used as the pin.

## Files

| file | role |
|---|---|
| `frame.json` | pre-registration: object under test, 52 declared pins, rules, controls, falsifier (sha in `frame.sha256.txt`) |
| `census_070_pinbind.py` | read-only deterministic instrument (`--preregister`, `--run`); no network, no numerics, no canonical writes |
| `report.json` | machine result: per-pin verdicts, leg-by-leg triple binding, mirrors, controls, drift, auxiliary input hashes |
| `addendum.json` | characterisation of the two stream gaps + currency check |
| `run.log` | instrument log |
| `SHA256SUMS.txt` | hashes of the above |

Inputs are pinned in `report.json` (`auxiliary_inputs_start/end`): map
`a2585ffc2152…`, registry `00090c50dd75…`, events `d559e570451f…` at run time (stream
continues to move; that is why the stream legs are snapshot-bound).

## Not claimed

No gate verdict, no node transition, no review verdict, no claim about schema content or
class binding, no statement about actor intent, no claim about any revision other than the
measured bytes. Workers cannot set `done`/`passed`/gate verdicts (PROTOCOL rule 2).

## Falsifier

Re-run `census_070_pinbind.py --run` at FROZEN
`815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`: falsified if either gap
path's latest-by-`created_at` event resolves to the FROZEN pin, if
`e6b1af2bd692…`/`276009f4f63d…` is shown to be live bytes at the declared path, or if the
measured FROZEN/disk/registry legs disagree. A FROZEN hash change voids the run.
