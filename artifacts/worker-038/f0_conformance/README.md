# W038-F0-CONFORMANCE-01 — independent F0 conformance check

Bounded execution worker `worker-038`. Node **F0**, gate **G-F0**, classes
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`.

## Task

After the rev26 role-separation adjudication, G-F0 has **0 independent accepts** at the
measured canonical hash while four earlier revise/inconclusive verdicts predate rev26.
This run executes an independent conformance check of the canonical F0 taxonomy against
the machine-checkable G-F0 criteria and the A0 rubric frozen-class axes, and issues a
hash-bound `accept`/`revise` verdict.

## Reviewed revision (snapshot pinned)

| input | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (rev4, `draft_unverified`) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f` |
| `evaluation_rubric.yaml` (A0) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `artifacts/formulation/FROZEN.json` (rev26) | `2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3` |
| `artifacts/worker-01/validate_taxonomy.py` (declared checker) | `2cc8ee04023e2316ee47683802b0fc99c9358cc06bea824993d3ac85964a1cc3` |
| `check_f0_independent.py` (this worker) | `582e1b316c4f364ed3ae489c3b0649114a7d59af3bfdb2a6558b283d255c8b50` |

Byte copies of the first four inputs are in `snapshots/` with `SHA256SUMS`, so the
verdict stays bound even if the canonical path moves.

## What was run (`run_manifest.txt` records every command and exit code)

1. `python3 artifacts/worker-01/validate_taxonomy.py --self-test` → exit 0.
2. `python3 artifacts/worker-01/validate_taxonomy.py --json worker01_validation.json`
   → exit 0, **253 checks passed / 0 failed / 37 taxonomy cases**, verdict `pass`.
3. `python3 check_f0_independent.py --json independent_checks.json` → exit 0,
   **11 PASS / 0 FAIL / 2 NOTE**; input hashes identical before and after.

The declared checker is author-family tooling (its author drafted F0), so it is treated
as one input; the independent verdict comes from the separate checks in
`check_f0_independent.py`, which recompute the criteria from the parsed bytes:

- `IND-01` pins stable across the run;
- `IND-02` exactly 4 class ids, taxonomy set == rubric frozen set == `classes` keys;
- `IND-03` 6/6 disjointness pairs present and each named decisive axis recomputed to
  differ between the two class axis vectors (not read from the prose);
- `IND-04` G2: SCC classes exactly one token in {C0,C2}, WCC classes none;
- `IND-05` axis values inside `field_vocabulary`; one conclusion_type per class, C0/C2
  unmerged (the two WCC classes sharing `weak_cosmic_censorship` is expected);
- `IND-06` FROZEN.json `logical_artifacts` pins match measured canonical + supplement bytes;
- `IND-07` canonical/supplement role separation: identical class-id sets, disjoint role
  keys (`classes`/`class_ids` vs `class_contracts`/`frozen_classes`/...);
- `IND-08` independent merged-regularity scan: 0 hits in the four class blocks; whole-file
  hits are prohibition/guard/vocabulary text (`IND-08-OBS`, non-blocking);
- `IND-09` no theorem-status promotion (`status: draft_unverified`, `claims_theorem_status: false`);
- `IND-10` both variants are parent-bound pointers carrying falsifiers, not class ids;
- `IND-11` A0 rubric frozen-class axes agree under an explicit vocabulary mapping
  (`none_required`↔`none_assumed`, `SCC-C2/C0`↔family+token, `Lambda = 0` in hypotheses).

## Verdict

`accept` — independent worker evidence for the G-F0 machine-checkable criteria at
`276009f4f63d`. Residual observations (`OBS-01` conclusion-label vocabulary divergence
rubric↔taxonomy; `OBS-02` provisional genericity placeholders; `OBS-03` declared
`CG1` coverage gap) are non-blocking and travel with the verdict.

## What this is not

Not a gate verdict, not a node-completion claim, not a physics judgement. A worker event
cannot set `status=done`, `validation_status=passed` or a gate verdict
(`comms/PROTOCOL.md`; ASTRA_HANDOFF authority note). The reviewer is not an author of F0,
the supplement, the rubric, the manifest or the declared checker.

## Falsifier

A reader who (a) shows an id/symmetry/matter/conclusion axis is misread here, (b) exhibits
a merged-regularity string the `IND-08` normalization misses in a class block, (c) shows a
taxonomy case naming a non-frozen class or unresolved hypothesis, or (d) shows a
canonical/supplement class-id mismatch, refutes the corresponding PASS; any substantiated
FAIL flips the verdict to `revise`.

Re-run: `bash artifacts/worker-038/f0_conformance/run.sh` then
`python3 artifacts/worker-038/f0_conformance/build_report.py`.
