# W075-FORM-BINDING-SWEEP-07

Bounded class-bound worker task taken by `worker-075` (no inbox card existed for slot 075).
Classes **AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN** (plus the F0 declared taxonomy);
node F1/F2a/F2b/F0; gate **G-FORM/G-F0**. Read-only with respect to every canonical and shared
artifact: the sweep writes only `binding_sweep_075.json` and the `_checker_replay/` scratch under
this directory.

## Why

`astra-life05-evidence-binding-repair` re-froze the three class schemas (rev13) and published
FROZEN rev29. Before any G-FORM accept can bind a pin, an independent instrument must confirm
that (a) every FROZEN pin matches live bytes, (b) every declared `*sha256` in the frozen
artifacts resolves to the path it names, (c) the consistency-evidence chain is intact and
reproducible, (d) the three mirrors are byte-aligned, (e) the rev12→rev13 change is confined to
the authorised repair set, and (f) the F1 strictness-direction correction moved in the proved
direction.

## Instruments

| file | role |
|---|---|
| `sweep_form_bindings_075.py` | deterministic sweep, S1–S10 checks |
| `binding_sweep_075.json` | main evidence artifact (per-file hashes, per-pin rows, findings) |
| `verify_binding_sweep_075.py` | independent verifier + 6 negative controls on copies |
| `verify_binding_sweep_075.json` | verifier report (PASS/FAIL, per-control result) |

The sweep itself never runs `check_taxonomy_consistency.py` (that tool unconditionally rewrites
the canonical evidence file). Instead S4b executes a copy of the pinned checker with both `ROOT`
and the output path redirected into this directory; the replay is byte-compared to the pinned
evidence. This is the only way to check "the pinned evidence is the checker's output" without
mutating a frozen path.

## Headline result at FROZEN rev29 (`artifacts/formulation/FROZEN.json` sha256 `815e08079aef…`)

Clean: 0/50 pin mismatches, 0 declared-hash mismatches, 0 consistency-chain findings,
checker replay byte-identical to the pinned `taxonomy_consistency.json` (`9e335e9ba1bf…`),
0/3 mirror divergences, 0/36 unbound taxonomy-case rows, 0 unauthorised semantic changes vs the
pinned rev12 snapshots, 0 foreign class tokens or composite phrases in assertive fields
(4 metalinguistic mentions correctly excluded), F1 strictness model T1/T2/T4 verified and the
D5/variant-SET direction text corrected. Verifier: **PASS, 6/6 controls detected**.

## Freeze-order observations (reported, not gate verdicts)

- FROZEN rev29 was re-issued in place: the 00:55:02 manifest and the 00:57:26 manifest carry the
  same `revision: 29` but different bytes. At 00:57:0x five pins (VARIANT_REGISTRY, the rev29
  repair report, `regenerate_frozen.py`, the SET/CH variant deltas) did not match disk; the
  00:57:26 re-issue fixed them. Reviewers must bind the manifest **sha256**, never the revision
  label.
- `gate_test_report.json` and `taxonomy_consistency.json` are rewritten in place after the freeze
  by live checker loops with unchanged bytes (mtime newer than the manifest). Byte-stable, but
  any future version change in a writer would move a pinned path without an artifact event.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-075/form_binding_sweep/sweep_form_bindings_075.py
python3 artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.py
```

## Falsifier

Re-run the sweep + verifier at the same bytes: the report is falsified by (a) any FROZEN pin that
does not match disk, (b) any declared hash that does not equal its named path's measured hash,
(c) a checker replay that does not reproduce the pinned evidence bytes, (d) any unauthorised
semantic diff against the rev12 snapshots, or (e) any of the six controls not being detected.
A later FROZEN revision voids the numbers until the sweep is re-run.

Worker evidence only: no node status, `validation_status` or gate verdict is set here.
