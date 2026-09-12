# W029-F1-REV13-REOBSERVE-01 — F1 suite re-observation against live rev13

**One class-bound task.** Node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`.
Read-only worker measurement; no canonical byte written, no gate verdict, no node status.

## Question

REC-36 item (6) folds into the rev14 / FROZEN rev30 revision a rebind of all 25 rows of
`schemas/f1_falsifier_tests.jsonl` (`56bcb4b3234b`) to the live F1 pin plus re-observation of
`F1-AMB-11` / `F1-AMB-17` / `F1-AMB-23` against the rev13 text. Rev13 (`d9cebb9404b2`) moved the
visibility-strictness directions. Does any row's stored probe actually read the moved content, and
would a sha256-only rebind leave a row green while the substance it relies on changed?

## Result (verdict: `reobserve_required__no_mechanical_flip__direction_unpinned`)

| measurement | value |
|---|---|
| rows / probes | 25 / 84 |
| rows bound to superseded rev12 `cce9c60146d6` | **25 / 25** |
| rows citing live rev13 `d9cebb9404b2` | **0 / 25** |
| changed leaves rev12 -> rev13 | 12 (substantive, not bookkeeping) |
| rows whose probes read changed content | 4 — exactly `F1-AMB-11, 17, 23, 25` |
| rows with a recomputed probe mismatch | 1 — `F1-AMB-25` only (pre-existing) |
| probes asserting the corrected direction (STRONGER/WEAKER) | **0 / 84** |
| probes reading any `relation` leaf | **0** |
| measurement digest | `467d2e75f1ae` |

**No named row flips mechanically against rev13** — every stored `pass` still recomputes. The
finding is narrower and sharper than a defect: the rows are *substantively* stale while being
*mechanically* green, so a hash-only rebind would pass every binding check and re-observe nothing.

## Per-row re-observation

| row | deciding field | changed leaf | mechanical | substance |
|---|---|---|---|---|
| `F1-AMB-11` | `visibility.definition` | `visibility.definition` (EXACT) | unchanged_pass | changed |
| `F1-AMB-17` | `visibility.definition` | `visibility.definition` (EXACT) | unchanged_pass | changed |
| `F1-AMB-23` | `class_identity_variants` | `[0].relation` STRONGER->WEAKER | unchanged_pass | changed |

Rev14 must, per row:
- **F1-AMB-11** — refresh the stored excerpt of `visibility.definition`; it quotes only the
  unchanged prefix and does not carry the rev13 equivalence statement. `resolved_geodesic` stands.
- **F1-AMB-17** — keep `NOT equivalent` on the *unchanged* leaf `visibility.negation_conclusion`
  (single-point vs open-set). Do **not** retarget it at `visibility.definition`, which now asserts
  the *tail vs whole-curve* EQUIVALENT on the same block. Whole-block equivalence greps conflate
  the two claims. Re-observe probe[0] and record that the field moved for an unrelated correction.
- **F1-AMB-23** — the direction its container now carries is covered by **no probe**; either add a
  direction probe on `class_identity_variants[0].relation` or record explicitly that
  `is_this_class=false` is direction-independent. The row also has `schema_snapshot: null` and
  `schema_under_test: null`, so it declares no schema revision under test.

Findings `W029-R13-01 … -06` are machine-readable in `report.json`.

## Method and independence

- `check_f1_rev13_reobserve.py` re-implements the probe semantics independently
  (`contains` / `equals` / `path_exists` / `nonnull` / `is_none` / `is_true`, `json.dumps`
  flattening) and recomputes all 84 probes against the live rev13 bytes.
- The rev12 snapshot is taken from **three** independent on-disk copies (workers 007/060/088),
  byte-identical (`K6`); the rev13 bytes are corroborated by **four** further independent copies
  (workers 040/060/082 and 007), all equal to the live pin (`K7`).
- Controls: `K1` unknown kind fail-closed, `K2` determinism, `K4` probe sensitivity (token
  deletion flips `F1-AMB-11` probe[1]; the mutation is asserted to remove the substring so the
  control cannot pass vacuously), `K5` the known `F1-AMB-25` mismatch reproduces, `K6`/`K7`
  corpus integrity. All pass. `E1`–`E15` all hold; zero pin drift T0->T1.
- The `K4` control initially returned **false** because the first mutation (`TAIL` -> `TAILX`)
  left the searched substring intact. The mutation was corrected to delete the token; that
  false-pass is retained here as a process note rather than silently fixed.

## Falsifier

Re-run check_f1_rev13_reobserve.py at the same declared pins: falsified if any named row flips mechanically against rev13; if the F1-AMB-25 mismatch set does not reproduce; if a probe is found asserting STRONGER/WEAKER or reading a `relation` leaf; if the rev12->rev13 delta is not the 12 declared leaves; or if any declared pin moves T0->T1.

## Deliverables

- `check_f1_rev13_reobserve.py` — checker, exit 0 complete / 2 failed expectation / 3 pin drift
- `report.json` — full machine-readable report, digest `467d2e75f1ae`
- `PREREGISTRATION.json`, `evidence.json`, `CHECKPOINT.json`, `pinned/`, `SHA256SUMS`
