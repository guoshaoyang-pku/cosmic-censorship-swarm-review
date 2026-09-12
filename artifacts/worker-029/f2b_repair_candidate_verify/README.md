# W029-F2B-REPAIR-CANDIDATE-VERIFY-01

Worker `worker-029`, 2026-09-12T01:12:24+08:00. Node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.
Read-only on every canonical path; no gate/node/validation status moved.

## Task
Independently verify the two F2b repair candidates staged by worker-080
(`candidate_corrected 51c253c4`, `candidate_nesting_only 4951cc96`) and the circulating
2-edit repair (`84b5d3fa`) at the live rev13 pin, with an independently written checker.

## Result
| target | sha256 | findings |
|---|---|---|
| live F2b rev13 | `b2ab6acb2bbe` | `false_containment_denial`, `size_premise_inverted` |
| circulating repair | `84b5d3fa29a6` | **`entailment_direction_inverted`** (repair-introduced) |
| corrected candidate | `51c253c46306` | none |
| nesting-only candidate | `4951cc969803` | none |
| rev12 candidate | `98f9ec83c487` | `entailment_direction_inverted` |
| C2 sibling | `e9a27996dfd3` | none |
| F1 sibling | `d9cebb9404b2` | no F2-style defect (no chain by design) |

- `live + patch_corrected.diff` reproduces `51c253c4` byte-exactly (`hash_reproduction: true`).
- `check_class_schema.py` returns rc 0 for live and all three candidates: the canonical
  structural gate is **blind** to all three defect kinds (independent confirmation of
  worker-017/worker-080).
- 14/14 pre-registered controls match, including class-relativity C13/C14: the same sentence
  `H2_loc-inextendibility entails this class's conclusion` is **accepted under own=C2 and
  rejected under own=C0**, so the checker is direction- and class-relative, not string-matching.
- Any pinned byte moving voids the report (`t1_live_remeasurement` in `evidence.json`).

## Landing requirements measured (owner-only)
1. Adopt `candidate_corrected 51c253c4` or `candidate_nesting 4951cc96`; do **not** land
   `84b5d3fa` as-is.
2. Bump revision, update `revised_at`, mirror to `artifacts/formulation/schemas/`, re-emit the
   FROZEN manifest, re-run the taxonomy-consistency evidence.
3. Fixture disposition: 35 semantic-contract fixtures still embed the
   stale strings (see `blast_radius.json`); canonical normative carriers are only
   `schemas/af_scc_c0_vacuum.yaml` and its authoring mirror.
4. Re-run `check_f2b_repair_candidates.py` after the bump; it fails closed on pin drift.

## Files
`check_f2b_repair_candidates.py`, `report_core.json` (deterministic), `report.json`,
`evidence.json`, `blast_radius.py` / `blast_radius.json`, `pinned/` (byte copies), `SHA256SUMS`.

## Falsifier
Re-run this script on the same pinned bytes: falsified if any pin moves, if live does not yield exactly {false_containment_denial, size_premise_inverted}, if candidate_corrected 51c253c4 or candidate_nesting 4951cc96 yields any finding, if circulating 84b5d3fa does not yield entailment_direction_inverted, if the class-relativity controls C13/C14 swap, if any other control departs from its expectation, or if live+patch_corrected does not reproduce 51c253c4.
