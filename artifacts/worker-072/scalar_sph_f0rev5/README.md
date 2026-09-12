# W072-D — AF-WCC-SCALAR-SPH conformance re-measurement at F0 taxonomy rev5

Bounded class-bound task, worker-072, 2026-09-12. No assignment card existed for
worker-072 in `comms/inbox/`; the task was self-selected from the standing
G-FORM/G-F0 requirement and from this worker's own open thread (W072-A → W072-C).

## What this closes

* **HF-W072C-1** (my own hard failure against the W072-A detector): the H2 check
  matched the substring `spherical` inside `non-spherical`. This implementation
  reports the bare token only under an explicitly labelled comparability reading
  and uses the negation-aware form for every conformance claim.
* **Stale pins**: W072-A/W072-C measured at `276009f4f63d` / `ce42d205e761`.
  Both moved. This run re-pins to the current canonical revisions and re-measures.
* **New conclusion predicate**: taxonomy rev5 repaired the class conclusion to the
  canonical tail predicate. This run measures discharge against the *repaired*
  wording, not against the `conclusion_type` token alone.

## Pins (sha256, all stable across the run)

| path | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |

Byte-identical copies of all three are in `snapshots/`; the runner aborts `rc=2`
if neither the live path nor the snapshot matches the pin.

## Result

* 10 ledger entries are bound to `AF-WCC-SCALAR-SPH`; **0 discharge** the class
  conclusion under every reading (legacy token, negation-aware loose, data-space,
  strict) and 0 claim the superseded SET variant. W072-A/W072-C's
  conclusion-poor headline survives the conclusion repair.
* In-class counts: bare token 4, negation-aware loose 4, data-space 3, strict 2.
  The target's 5 is not reproduced by any reading here (mechanism per W072-C:
  negated `spherical` forms in T-105/T-106).
* Recall scan: 4 unbound loosely-conforming entries (D-007, T-501, T-514, T-521),
  none naming H4 and none carrying a WCC conclusion.
* Citations: 14/14 class-bound rows carry a resolvable locator; stripped-locator
  control flagged.
* Controls: 7/7 (vacuum excluded, full tail-predicate mutant discharged, SET-only
  mutant *not* discharged, non-spherical rejected, Lambda excluded, unbound
  recall, H4-detector sensitivity).
* Taxonomy mechanical checks: 13/14. The failing check is `HF-W072D-1`.

## Finding HF-W072D-1 (hard-candidate, F0 class-definition consistency)

`research_map/formulation_taxonomy.yaml#classes.AF-WCC-SCALAR-SPH` at
`0abb9ed8a961` simultaneously carries:

* `hypotheses.H4.unresolved = true`, text: the genericity notion
  "(dense-open versus full-measure) is unresolved and must be named before any
  claim is filed";
* `axes.genericity_kind = "unresolved"` and
  `genericity_value_status = "unresolved_pending_L1"`;
* a conclusion that already names one: "For a **comeager** set G of data in the
  class …".

These cannot all be canonical at one revision. Falsifier: a note at this hash
declaring the conclusion's `comeager` a placeholder, or H4 updated to name
`comeager` with L1 status — re-running the detector must then read
`H4_vs_conclusion_genericity_consistent = true`.

## Scope limits

Mechanical class-conformance measurement only. No mathematical, physical or
citation-scope correctness is decided; no class re-binding; no node done; no gate
verdict; no theorem. Worker verdicts are advisory evidence.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-072/scalar_sph_f0rev5/verify_scalar_sph_f0rev5.py
# rc=0, report.json rewritten; result_digest must stay
# 0e7319dc491977561c912f7177e01b7e6b52c7a5030c9fe3974de9c17de0741a
```

Owner-side external control (live paths):
`python3 artifacts/formulation/tools/check_taxonomy_consistency.py` → rc 0,
`CONSISTENT (4 classes, 0 contract-text divergences)`; raw output in
`raw/check_taxonomy_consistency.json`.

## Hashes

* runner `verify_scalar_sph_f0rev5.py`:
  `26a78f3d9e12f81cf16d71b2aaba0e11c8aca111de971cfe2631b97d31219f92`
* report:
  `44b4baf8aa69befba71b10353d61faac69917790a7a6b54ed74495b35b54405d`
* result digest (deterministic core):
  `0e7319dc491977561c912f7177e01b7e6b52c7a5030c9fe3974de9c17de0741a`
