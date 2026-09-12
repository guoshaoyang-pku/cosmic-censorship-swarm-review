# W030D-F1-PROVENANCE-CLOSURE-01 — the FROZEN rev29 repair record is reproducible from its pinned inputs

- **Worker:** worker-030 (bounded execution worker; one class-bound task, then exit)
- **Classes / nodes / gate:** `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` · F1 / F2a / F2b · G-FORM
- **Card audited:** `astra-life05-evidence-binding-repair` (REC-12)
- **Closes / narrows:** `W030C-F1` in `artifacts/worker-030/rev13_preflight/report.json` (see §"Relation to W030C-F1")
- **Instrument:** `artifacts/worker-030/f1_provenance_closure/run_closure.py`
- **Machine report:** `artifacts/worker-030/f1_provenance_closure/report.json`
- **Reproduce:** `python3 artifacts/worker-030/f1_provenance_closure/run_closure.py` (read-only; writes only its own `report.json`; exit 0 iff no finding)

## Verdict

```
F1_PROVENANCE_CLOSED_VALUE_REPRODUCED_FROM_PINNED_INPUTS
  C1  the unpinned key after_pre_binding_fix = repair_f1(rev12, report.at)   MATCH
  C2  live F1 == intermediate + the declared correction composition          byte-identical
  C3  live F2a == binding branch(rev12, report.at)                           MATCH
  C4  live F2b == binding branch(rev12, report.at)                           MATCH
  C7  controls: wrong timestamp differs; binding branch rejects the intermediate; external
      rev12 copy reproduces the same key
  D   12 guarded inputs, zero drift
```

## What was decided

`FROZEN.json` rev29 (`815e08079aef`) pins the repair report `#3379bcfb` and its generator
`#2f6c4f7d`, but the report carries the key `after_pre_binding_fix = bf0c28fa673e…` and the pinned
generator source contains that key **0 times**. W030C-F1 read this as a provenance defect.

This instrument shows the key is not an orphan. It is the value of

```
repair_f1(rev12_AF-WCC-VAC-GEN_bytes, "2026-09-12T00:53:20+08:00")   ->  bf0c28fa673e5bd5…
```

i.e. the F1 **first-apply intermediate state** (item 3 applied, item 2 not yet), at the timestamp
the report itself records in its `at` field. The corrected generator then composed the item-2
binding refresh into the same rev13 without a second header bump, yielding the live bytes:

```
live F1 d9cebb9404b2  ==  binding_edits(intermediate + rev13 note extension)   byte-identical
```

So all three frozen rev13 schemas are deterministic functions of (a) the rev12 pinned bytes,
(b) the pinned generator `#2f6c4f7d`, and (c) timestamps recorded inside the frozen report:

| class | rev12 | operation at 00:53:20 | live rev13 |
|---|---|---|---|
| `AF-WCC-VAC-GEN` | `cce9c60146d6` | `repair_f1` → `bf0c28fa673e` (the unpinned key), then item-2 composed | `d9cebb9404b2` |
| `AF-SCC-C2-VAC-GEN` | `5476a3f2c6bc` | `repair_binding` | `e9a27996dfd3` |
| `AF-SCC-C0-VAC-GEN` | `55d0a1ea9bda` | `repair_binding` | `b2ab6acb2bbe` |

The only remaining gap is **record-keeping, not content**: the pre-fix wrapper that *emitted* the
extra key is not itself pinned. Its output value is fully reproduced; its source is not. Pinning
that wrapper version (or dropping the key in a new revision) would make the frozen record
byte-provenanced end to end. Reported as a blocker, not adjudicated here.

## Why this is independent

- The pinned tool is **not imported**. Its literals are extracted by `ast` from the pinned bytes;
  the header bump, substitutions and composition are reimplemented from scratch in the instrument.
- All timestamps come from the report's own `at` and the correction's declared composition time.
  No wall-clock input; two runs produce identical output.
- The instrument re-derives the report's own `before` pins from a separate rev12 snapshot
  (`artifacts/worker-030/frozen_transition/snapshot/`, taken 00:33) and reproduces the key from a
  **second, external** rev12 copy (`artifacts/worker-033/gform_r12_ledger/pinned/canonical/`).
- Controls (C7): the reproduction is timestamp-sensitive (00:53:41 gives `a503f2ea…`, not the
  target), and `repair_binding` **fails closed** on the intermediate (`revision is 13, expected
  12`) — which is exactly why the correction had to compose the edits rather than call it.

## Relation to W030C-F1

| | W030C (00:58) | W030D (this) |
|---|---|---|
| unpinned key | reported unverifiable | reproduced from pinned inputs |
| live F1 vs intermediate | not connected | byte-exact composition verified |
| F2a/F2b | pins verified | branch reproduced byte-exactly |
| residual | "record not regenerable" | "emitting wrapper version unpinned" |

W030C-F1's falsifier — *"exhibit a version of `evidence_binding_repair_rev29.py` at the pinned hash
`2f6c4f7d` that emits `after_pre_binding_fix`, or a pinned instrument that does"* — is **met in
substance**: the pinned instrument at `2f6c4f7d` computes exactly that value for the F1 branch; the
pre-fix wrapper merely wrote it into the report. What is still missing is the wrapper's source
identity, not the value's provenance.

## Falsifiers

- Produce rev12 F1 bytes at `cce9c60146d6` whose `repair_f1(., 2026-09-12T00:53:20+08:00)` is not
  `bf0c28fa673e5bd5d82d03ab93059b99580af0f3f65a81d4924e0bc8e74a6226`.
- Produce live F1 bytes at `d9cebb9404b2` that differ from the composed candidate, or an
  intermediate→live diff with a changed region other than the two classified ones.
- Produce F2a/F2b rev12 bytes at `5476a3f2c6bc` / `55d0a1ea9bda` whose binding branch at
  `2026-09-12T00:53:20+08:00` does not give `e9a27996dfd3` / `b2ab6acb2bbe`.
- Show any of the 12 guarded input hashes moved during the run.

## Not claimed

No gate verdict, no review verdict, no node-status change, no canonical write, no mathematics or
physics claim. The wrapper-provenance residual is reported, not adjudicated. `FROZEN rev29` here
means the manifest at `815e08079aef` (50 files, `frozen_at` 00:57:26); reviews must cite the
manifest sha256, not the revision number.
