# W052-L0-HF02-REMAP-VERIFY-01 — independent verification of worker-023's HF-02 adjudication

**Worker:** worker-052 · **Node:** L0 · **Gate:** G-LIT ·
**Classes:** `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN`
**Verdict:** `VERIFIED_ACCEPT` (advisory; no gate verdict, no node status, no ledger edit)

## Target

| field | value |
|---|---|
| artifact | `artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json` |
| sha256 | `0f86158c5bb79adac957a4585a6be4b62abf13c541ea74769f9e629749c4f9d6` |
| author | worker-023 |
| author self-verification | `artifacts/worker-023/l0_hf02/hf02-verify-023.json` (same author — not independent) |
| applied | `false` (proposal only) |

## Question

`evaluation_rubric.yaml` HF-02 `class_leakage` (severity **critical**) fires on a
*disjunction of class_ids*. At the pinned ledger hash, 8 L0 rows carry two frozen classes in
`class_ids` (D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528). worker-023 proposes a
not-applied remap of those rows into the `VARIANT_REGISTRY.json` variant scheme
(variant tag + `informs_classes`), predicting 0 remaining disjunctions.

This harness asks: **is that packet correct, complete, and reproducible by an independent
checker?** It was written from the frozen rule text, does not import or execute worker-023's
builder/verifier, and is read-only.

## Pinned inputs (all re-hashed at run time)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |

## Checks (all PASS)

| id | check | result |
|---|---|---|
| P1 | seven pins re-hash to the packet's declared values | PASS |
| R1 | disjunctive set independently re-derived from the live ledger == packet's 8 named rows | PASS |
| R2 | every packet `class_ids_at_pin` and `row_evidence` field equals the live ledger row; packet row-set integrity (8/8) | PASS |
| R3 | every recommendation shape-valid: `class_ids`/`informs_classes` ⊆ frozen four, disjoint, non-empty binding, no variant id in `class_ids`, tag adds registered | PASS |
| R4 | each cited extension class is a registered variant with the declared parent and a registry-stated containment direction | PASS |
| R5 | in-memory patch: 0 disjunctions, 0 unknown tokens, 0 variant ids in `class_ids`, 0 duplicates; 2 newly singular (T-515, T-528); 6 relation bindings — matches packet summary | PASS |
| R6 | patch application is idempotent | PASS |
| R7 | ledger sha256 unchanged after the run (read-only) | PASS |
| R8 | rubric HF-02 text contains the disjunction clause | PASS |

## Controls (6/6 discriminate)

`C0` clean inputs pass. `C1` a registered variant injected into `class_ids` is caught
(unknown-token + evidence-binding). `C2` a 9th synthetic disjunctive row is caught
(completeness). `C3` a tampered `row_evidence` field is caught (evidence binding). `C4` an
altered pin hash is caught. `C5` a dropped packet row is caught (row-set integrity).

## Advisory findings (reviewer judgement, not hard failures)

- **W052-A1 — T-303 rationale direction.** The packet calls T-303 "a counterexample inside the
  L2CONN variant". It is a C0 extension whose Christoffels are *not* in `L^2_loc`, so it is a
  counterexample to the C0-regularity statement on a special (non-generic, impulsive) data class
  and a strictness witness for `E_L2conn ⊊ E_C0`; it does **not** refute the L2CONN statement,
  which forbids only extensions whose Christoffels **are** in `L^2_loc`. The recommended binding
  (`class_ids=[]`, `informs=[AF-SCC-C0-VAC-GEN]`, tag `L2CONN`) is unaffected.
- **W052-A2 — D-005 scope.** D-005 defines Lipschitz `C^{0,1}_loc` **or** continuous metric with
  Christoffel in `L^s_loc` for `s>1`; the remap registers only `LIP`. The `s>1` family (of which
  `L2CONN` is `s=2`) has no registered variant id. HF-02 clearance is unaffected.
- **W052-A3 — post-patch class-binding metrics (scope).** Before → after: `class_ids` empty
  28 → 34; no binding at all 21 → 21; singular frozen `class_ids` 26 → 28; A0 `class_binding`
  fraction 0.4194 → 0.4516. The L0 `stop_rule` clause "the class column is non-empty" holds for
  the remapped rows only if the class column is read as `class_ids ∪ informs_classes`; under a
  `class_ids`-only reading the patch looks like a regression (34 → 28 non-empty). Owner-level
  interpretation decision, not an HF-02 defect.
- **W052-A4 — validity window.** The packet and this verification are void at any ledger hash
  other than `a1674f0949…`; re-run on hash move.

## Falsifier

Falsified if (a) any pinned input re-hashes differently; (b) the independently re-derived
disjunctive set differs from the packet's 8 rows; (c) any packet `row_evidence` field differs
from the pinned ledger row; (d) the in-memory patch leaves a disjunction, an unknown class
token, a variant id in `class_ids`, or a duplicate; (e) any mutation control C1–C5 is not
caught or C0 fails; or (f) `ledger/theorems.jsonl` changes from the pinned hash.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-052/l0_hf02_verify/verify_hf02_remap_052.py   # exit 0 iff all checks + controls pass
```

Report: `artifacts/worker-052/l0_hf02_verify/report.json`. Canonical files were not modified.
