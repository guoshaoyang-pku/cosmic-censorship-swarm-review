# FORM-GEN-05 — re-bind to FROZEN rev28 / schema rev12 (delta report)

Worker: `deepseek-flash-15` (slot `worker-015`) · Node `F1` · Class scope
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` · Gate `G-CLASSBIND`
Status: **advisory measurement, not a verdict; no completion claimed.**

This is the bounded stop-rule run of assignment `assign-FORM-GEN-05-20260911T2331`
("re-run your N1–N5 acceptance against the rev2 hashes and report deltas only"). The
matrix itself is frozen at `509f9f2e1a9f` and was **not** edited.

## Pinned inputs (freshly measured at run time)

| artifact | sha256 (prefix) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev12) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (rev12) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (rev12) | `55d0a1ea9bda` |
| `research_map/formulation_taxonomy.yaml` (declared F0 rev5) | `0abb9ed8a961` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev28) | measured this run |

All five FROZEN-declared file pins match the bytes on disk (checked field-by-field in
`rebind_rev28.json → checks.D0_frozen`).

## Delta vs the pre-rev12 baseline

Baseline `schema_alignment_precheck.json` (same matrix `509f9f2e1a9f`, schema drafts at
`7a3e1f93` / `21df6f7f` / `0150bfdf`): **hard = 10, warn = 3**.

At rev12: **hard = 0, warn = 0**, and the official gate tool
`artifacts/formulation/tools/run_gate_tests.py` (`78509c9eb8b1`) reports
`GATE TEST REPORT: PASS`, canonical 3/3, null controls 6/6, mutants 31/31 (raw stdout:
`gate_run_rev28.txt`). The rev12 rewrite closed every R07 key/kind/`is_part_of_class`
finding the precheck raised, including the prose-`kind` conflation that produced the 10
hard findings. **No regression; the delta is a strict improvement.**

## The one surviving gap (non-blocking, for the owner)

`rebind_closure_rev28.py` computes the full transfer closure that the schemas *entail*
from their declared `transfer_failures` / `transfer_holds` / `variants[].statement_strength`
(variant strengths are read as comparisons against the class default `residual_comeager`).

- **Contradictions: 0/36.** No schema entails the opposite of the matrix.
- **Silent: 6 of 12 ordered pairs, identically in all three classes.** These are
  unencoded, not wrong. Five involve the `full_measure` kind
  (`full_measure→open_dense_escape`, `full_measure→finite_codimension_complement`,
  `open_dense_escape→full_measure`, `open_dense_escape→finite_codimension_complement`,
  `finite_codimension_complement→full_measure`); the sixth is the *holds* row
  `finite_codimension_complement→open_dense_escape`.

R07 requires only that `transfer_failures` be non-empty and that the notion not be a free
parameter, and that is satisfied. The gap is therefore reported as **backlog
clarification**, not a blocker: if the owner wants the schemas to carry the matrix's full
12-pair relation rather than 6 declared edges plus derivations, those six rows are the
exact patch list. Note the matrix's `finite_codimension_complement→full_measure` row is
`open` (it is conditional on a declared measure with `mu(Z)=0`); the schema currently
states no measure hypothesis there.

## Falsifier

Re-run `python3 artifacts/flash-15/genericity/rebind_closure_rev28.py`. This delta report
is void if (a) any of the three schema hashes changes — the run then measures a different
revision and must be re-bound; (b) the script reports a hard contradiction
(schema-entailed opposite of a matrix row); or (c) the official gate tool no longer
reports PASS at the pinned hashes.

## Files

- `rebind_closure_rev28.py` / `rebind_closure_rev28.json` — the closure measurement.
- `rebind_rev28.py` / `rebind_rev28.json` — earlier naive closure; kept only as the
  record of the over-reporting (it counted schema *silence* as disagreement). Superseded
  by the closure run above; do not cite its `hard=15`.
- `gate_run_rev28.txt` — raw stdout of the official gate tool at the pinned hashes.
- `schema_alignment_precheck.json` — the pre-rev12 baseline used for the delta.
