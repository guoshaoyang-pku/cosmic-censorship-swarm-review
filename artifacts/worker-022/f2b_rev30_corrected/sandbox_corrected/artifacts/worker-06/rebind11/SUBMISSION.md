# FORM-PROBE-11-REBIND-REV29 — submission (worker-006)

**One bounded, class-bound task.** Node `A1`, gate `G-CLASSBIND`, classes
`AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN`.
Pins: FROZEN **rev29** (2026-09-12T00:54:32+08:00); canonical schemas
`d9cebb9404b2` (WCC) / `e9a27996dfd3` (C2) / `b2ab6acb2bbe` (C0);
stage A `check_class_schema.py` `000e09e46b2f`; stage B `spec_conformance_audit.py`
`c79d8ab8440a`; calibrated stage B' `audit_calibrated_exempt11.py` `12ad9ebcc918`;
`rule_spec.json` `40f9bb9e657b`.

## Why this task

`FORM-PROBE-11` (predecessor, rev28) measured union escape **22/22 = 1.0000** for prose
leaks in schema surfaces the two-stage pipeline does not scan, and left the standing
falsifier: *"a later revision whose gate catches these fixtures (re-run the frozen
corpus, never this one)"*. FROZEN **rev29** then landed the `astra-life05` evidence-binding
repair (rev12 -> rev13), which **changed all three canonical schema hashes** and therefore
stale-bound the probe-11 evidence. This run executes that falsifier at the new bytes.

## Method (pre-registered, fail-closed)

- The `MUTANTS` list is **byte-identical** to FORM-PROBE-11; only the canonical bases are
  rebound to the FROZEN rev29 bytes. 31 fixtures: 3 canonical copies + 3 legitimate-negative
  controls + 3 sensitivity controls + 22 declared mutants.
- The generator re-asserts **single-leaf surgery** for every mutant (deep diff of the parsed
  docs changes exactly the declared target path); all 22 passed on the rev29 bases.
- `manifest.json` was hashed **before any stage run** (`preregistration.json`):
  `b83e62ade2912d3b153f9c0810560ab3e863fe7142b85741a0968169d033e168`. All pins were
  re-measured after the run: **zero drift, zero fixture-byte drift**.
- Stages: **A** canonical `check_class_schema.py` (R01-R31); **B** frozen worker-06 auditor;
  **B'** the same auditor with the single documented R03 binder-layout delta (the frozen copy
  falsely rejects canonical WCC at rev29 — unchanged from rev28); **B\*** hardened.

## Controls (all green)

| control | n | result |
|---|---:|---|
| canonical schemas pass A and B' | 3/3 | accept |
| legitimate negative-field statements pass A and B' | 3/3 | accept |
| sensitivity: same family content in an ASSERTIVE field is caught | 3/3 | A fires |

Corpus validity **VALID**. `run_rebind11.py --preflight` exits 0.

## Result

**Union escape 22/22 = 1.0000** at FROZEN rev29 (S1 8/8, S2 10/10, S3 4/4; high-load 7/7;
7 leak families). Structural escape 1.0000; calibrated semantic escape 1.0000.
Frozen stage B flags 7/22 — every one is the unchanged **R03 binder-layout false positive**
it also raises on the canonical WCC schema, so its genuine detection is 0/22.

**The standing falsifier is NOT triggered at rev29.** Per-fixture verdicts are **identical to
FORM-PROBE-11** (`verdict_diff_rev28_vs_rev29 = []`), and the rev29 delta touched **zero** of
the 22 declared mutant target leaves (`declared_target_collisions = []`).

## Rev28 -> rev29 delta map (`rebind_analysis.json`)

| class | old -> new | changed leaves | of which probed unscanned surfaces |
|---|---|---|---|
| AF-WCC-VAC-GEN | `cce9c60146d6` -> `d9cebb9404b2` | 12 | `revision_history[10].{at,index,unused,notes[0]}` |
| AF-SCC-C2-VAC-GEN | `5476a3f2c6bc` -> `e9a27996dfd3` | 9 | `revision_history[10].{at,index,unused,notes[0]}` |
| AF-SCC-C0-VAC-GEN | `55d0a1ea9bda` -> `b2ab6acb2bbe` | 9 | `revision_history[10].{at,index,unused,notes[0]}` |

Gate and rule tooling hashes are byte-identical to FORM-PROBE-11, so the rev29 repair could
not have changed stage-A behaviour except through the rebound bytes; the rebind confirms it
did not. Note that the repair itself **wrote a load-bearing explanatory note into
`revision_history[10].notes[0]`** — exactly the S3 metadata surface on which all four S3
mutants (e.g. `m05`, `m12`, `m13`) show zero detection by either stage.

## Deliverables (all under `artifacts/worker-06/rebind11/`)

`preregistration.json`, `manifest.json` (+`.sha256`), `report.json`, `raw_verdicts.json`,
`per_surface.json`, `blindspot_report.json`, `rebind_analysis.json`, `SUBMISSION.md`;
repro: `make_rebind11.py`, `run_rebind11.py` (`--preflight` / `--run`), `analyze_rebind.py`,
`emit_rebind11.py`.

## Falsifier

Any mutant caught by stage A (`verdict != pass`) or by calibrated stage B' (`verdict != accept`)
at the pinned hashes falsifies its escape entry; any pass control rejected, any pinned-hash
change during the run, or any fixture-byte drift voids the measurement; a rebind failing the
single-leaf assertion voids the corpus. A later revision whose gate catches these fixtures
falsifies the blind-spot claim at that revision only.

## Not claimed

No gate verdict, no node completion, no theorem, no physics result. Independent measurement
evidence only; interpretation is bound to the pinned hashes. This is a rebind, not a
byte-identical rerun: fixture hashes differ from FORM-PROBE-11 while verdicts match.
