# worker-087 / F0 closure check (`W087-F0-CLOSURE-CHECK-02`)

Bounded, class-bound task taken by worker-087 from the F0 immediate queue (no card was issued for
this worker in this lifecycle). One task, artifact-backed, checkpointed, then exit.

**Result:** `BLOCKING_FINDINGS_CLOSED_AT_0abb9ed8a961` — independent machine verification that the
three blocking F0 findings (`B-16F0-1`/`W082-F-01`, `B-16F0-2`, `B-16F0-3`) are discharged at the
frozen canonical revision `research_map/formulation_taxonomy.yaml` sha256 `0abb9ed8a961…`
(rev5, `FROZEN.json` revision 27), with an end-to-end negative control that re-detects the defect
when the pre-rev5 wording is re-introduced. Full narrative: [`CLOSURE.md`](CLOSURE.md).

**Scope:** targeted closure verification of three specific findings plus regression invariants.
**Not** a full-schema review, **not** a gate verdict, **not** a node-status change. Worker
authority only.

## Run it

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-087/f0_closure_check/run_all.py \
  --expect-pin 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3
# -> verdict, 3/3 bundle expectations PASS, exit 0

# single target, any revision:
python3 artifacts/worker-087/f0_closure_check/accept_f0_closure.py \
  --target research_map/formulation_taxonomy.yaml --pin <sha256>
# exit 0 = class-content CLOSED, 3 = OPEN, 1 = controls failed, 2 = drift/fail-closed
```

## Files

| file | role | sha256 (prefix) |
|---|---|---|
| `accept_f0_closure.py` | independent verifier: CL1–CL5 + INV1–INV4, 5 fail-closed controls, exit 0/3/1/2 | `d5ad33530e49` |
| `run_all.py` | pin-bound bundle: canonical verify → regression fixture → drift control → `results.json` | `c7fe723e0fb7` |
| `make_regression.py` | builds the negative-control fixture (pre-rev5 conclusion restored) | `a7dab55058d6` |
| `results.json` | aggregate report: verdict, expectations, per-finding disposition, pins, lead-side remainder, falsifier | `ca01dc19096f` |
| `results_canonical.json` | verifier report at the canonical frozen hash | `f48bac644266` |
| `results_regression.json` | verifier report on the negative-control fixture (`CL1`–`CL4` open) | `dc8a8a1b224c` |
| `regression_check.yaml` | negative-control fixture bytes | `31bac4037107` |
| `regression_edits.json` | surgery record for the fixture | `735fbe943f8f` |
| `fixtures/conclusion_bad_setbased.txt` | historical rev4 scalar conclusion (known-bad control) | `4150cd45cfc5` |
| `fixtures/conclusion_good_tail.txt` | repaired `AF-WCC-VAC-GEN` conclusion (known-good control) | `fa0d62015ff9` |
| `fixtures/conclusion_fixed.txt` | proposed fixed scalar conclusion (control + candidate source) | `830edcc78262` |
| `make_candidate.py` | **historical** rev4 repair generator (anchored, reversible, semantic-diff checked) | `421ee0babb74` |
| `formulation_taxonomy.candidate.yaml` | **historical** rev4 repair candidate, superseded by the lead's rev5 wording | `6207dfc091db` |
| `candidate.diff` / `candidate_edits.json` | rev4→candidate diff and edit table | `d8b5dce9102d` / `8fb7e3adaf1f` |
| `CLOSURE.md` | full closure narrative, evidence, scope limits, lead-side remainder | sidecar |
| `README.md` | this file | sidecar |

Every file above has a `.sha256` sidecar (written after this README; `README.md.sha256` covers this
file).

## What the checks decide

- **CL1** no class conclusion assertively carries the demoted set-based `J-(I+)` reading; WCC
  classes carry the single-q tail predicate, SCC classes none.
- **CL2** no class conclusion asserts an unsourced equivalence.
- **CL3** a class with `genericity_kind: unresolved` binds the deferral instead of using a bare
  generic quantifier.
- **CL4** `resolved_divergences[D3]`'s comeager claim is discharged per class (stated, or covered
  by an explicit named deferral in D3's scope note).
- **CL5** every `schema_owner` names the schema that declares that class and not a map-recorded
  legacy artifact.
- **INV1–INV4** exactly the four frozen class ids; axes vocabulary-legal with 6/6 disjointness
  pairs differing on a decisive axis; no duplicate YAML mapping keys; no merged C0/C2 spelling.
- **CL6/CL7** reported lead-side only: companion-pair adjudication (PASS at bundle time, REC-3) and
  downstream corpus re-pin (PENDING: 36 case records still carry
  `binding_status: bound_taxonomy_sha_66bf917bd368`).

## Provenance / non-duplication

The verifier is independent of `artifacts/worker-16/f0_review/check_f0.py`,
`artifacts/worker-082/**`, flash-02 tooling, `research_map/class_separation.py` and
`research_map/audit_evidence.py`. It deliberately overlaps worker-16's C10/C11/C13 detectors as an
independent third instrument; the additions are the frozen-hash closure decision, the end-to-end
negative control on the current bytes, the drift control, and the explicit lead-side remainder.
