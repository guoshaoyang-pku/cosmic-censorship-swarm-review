# W022-F2B-REV12-INDEP-VERDICT-01

Independent, hash-pinned, read-only verdict on **F2b** (`schemas/af_scc_c0_vacuum.yaml`,
class `AF-SCC-C0-VAC-GEN`) at the FROZEN revision 28 pin
`55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6`.

Taken from the live queue item `astra-life04-form-verify` (map.assignments, lead-audit:
"two independent blind reviewers per class at the FROZEN rev27 pins … F2b 55d0a1ea9bda,
each returning accept|revise|reject with a cited sha256 and hash-bound hard failures").
No assignment card exists for `worker-022` in `comms/inbox/`.

## Result

| check | severity | status | what it measures |
|---|---|---|---|
| C1 hash pin stability | hard | **PASS** | canonical == authoring mirror == FROZEN rev28 pin; `declared_f0_sha256` == measured F0 rev5; supplement measured; stable start→end |
| C2 declared evidence resolves | hard | **FAIL** | `f0_binding.consistency_evidence_sha256` = `675a99d0d25b…` but `artifacts/formulation/evidence/taxonomy_consistency.json` measures `9e335e9ba1bf…` |
| C3 evidence revision diff | info | — | live revision keeps `consistent=true` for the same four classes but drops `map_taxonomy_sha256`, `lead_contract_sha256`, `measured_at` |
| C4 duplicate keys (B1 closure) | hard | **PASS** | 0 duplicate keys at any depth; single top-level `revised_at` |
| C5 contract pointers (H1 closure) | hard | **PASS** | `class_contract_pointer` resolves at `classes.AF-SCC-C0-VAC-GEN` in canonical F0; supplement pointer resolves in the supplement |
| C6 D0 typing (H2/B2 closure) | hard | **PASS** | first quantifier `forall r in D0`; D0 is a tagged disjoint union (`smooth` \| `(sobolev,s,delta)`); no bare pair binder remains |
| C7 conclusion + leakage | hard | **PASS** | `conclusion_type: scc_c0_future_inextendibility` aliases F0's `strong_cosmic_censorship_C0`; no asserted C0/C2 composite; sibling contrast declared |
| C8 canonical structural gate | hard | **PASS** | `check_class_schema.py` → `pass`, `failed_rules=[]` |

**Verdict: revise, score 3.5.** One hash-bound hard failure: **HF-022-R1** — the F2b
class binding declares a consistency-evidence hash that no longer resolves at the
canonical path (the evidence file was regenerated after the rev12 freeze). No
class-semantics, typing, pointer or leakage defect was found in the pinned bytes. The
defect is a binding/re-stamp item, not a class-content item.

## Controls (all fired)

* **K1** wrong conclusion token (`scc_c2_future_inextendibility`) → C7 FAIL, as required.
* **K2** duplicate top-level `revised_at` reinserted → C4 FAIL, as required.
* **K3** dangling `class_contract_pointer` (`classes.AF-SCC-C0-NOPE`) → C5 FAIL, as required.
* **K4** pristine copy → C4–C8 all PASS (no false positives).

## Reproduce

```bash
python3 artifacts/worker-022/f2b_rev12_verdict/run_f2b_review_022.py
```

Read-only on canonical paths; writes only under `artifacts/worker-022/f2b_rev12_verdict/`
and (on the controller side) the review corpus. The script deliberately does **not** run
`artifacts/formulation/tools/check_taxonomy_consistency.py`, because that tool rewrites
its canonical evidence path.

## Files

* `preregistration.json` — pins, checks, controls, verdict rule frozen before measurement
  (`sha256 1d03f4884cf6…`).
* `run_f2b_review_022.py` — fresh stdlib+PyYAML checker (`sha256 07f823ca61ed…`).
* `f2b_review_report.json` — machine-readable report (`sha256 5f18667a2498…`).
* `pinned/` — byte snapshots of every reviewed input.
* `controls/` — the four control fixtures.

## Honesty note

The first execution of the checker returned `inconclusive` because the C7 sibling-contrast
check iterated over the characters of `sibling_disjoint_from`, which is a plain string, not
a list. That was a checker bug, not a schema defect. The one-line fix was applied and the
run repeated; the pre-registered criteria, pins and verdict rule were not changed. The
`K4` control now guards against that class of false positive.

## Non-claims

Not a physics verdict, not a theorem endorsement, not a gate verdict, no node transition.
Worker events cannot set `status=done`, `validation_status=passed`, or a gate verdict. Does
not review F1 or F2a. One reviewer label (ESS = 1).
