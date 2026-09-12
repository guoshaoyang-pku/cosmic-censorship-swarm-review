# W089-F2B-REV12-REVIEW-04 — F2b rev12 review at the FROZEN rev28 pin

**Worker:** worker-089 (bounded execution worker, no inbox card; task taken from
`reviews/G-FORM-final-verify.json` blocking item **B-GFORM-1**: F2b had 0 independent verdicts at
the rev28 hash).

**Target (read-only):** `schemas/af_scc_c0_vacuum.yaml`
sha256 `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` (revision 12),
authoring twin `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` = same sha256.
**Frozen pin:** `artifacts/formulation/FROZEN.json` revision 28, sha256
`2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1`.

**Class / node / gate:** `AF-SCC-C0-VAC-GEN` / `F2b` / `G-FORM`.
**Verdict:** `accept` (score 4.0), **not a gate verdict** — `counts_as_gate_accept: false`.
15/15 machine checks pass, 14/14 planted-defect controls caught, no-false-positive baseline
passes, no drift over the 90 s / 15 s stability window.

## Checks (report `f2b_review_report.json`)

| id | check | result |
|---|---|---|
| C01 | no duplicate top-level YAML keys | pass |
| C02 | `revised_at` wall-clock and mtime-consistent | pass |
| C03 | `revision_history` last entry `unused=false`, `at == revised_at` | pass |
| C04 | canonical contract pointer `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN` resolves and path equals declared F0 artifact (**HF-034-2 closure**) | pass |
| C05 | class-contract supplement pointer separate, resolvable, bound in `f0_binding` | pass |
| C06 | declared F0 hash equals measured canonical taxonomy hash | pass |
| C07 | FROZEN rev28 pins both paths, mirror equal, `frozen_at` not future | pass |
| C08 | class identity `AF-SCC-C0-VAC-GEN`, components C0, sibling `AF-SCC-C2-VAC-GEN`, no stray class token | pass |
| C09 | D0 tagged disjoint union, first binder `forall r over D0`, byte-identical across F1/F2a/F2b (**HF-034-1 closure**) | pass |
| C10 | extension predicate frozen at C0/none/future, clauses (a)-(f), caveat present | pass |
| C11 | conclusion typed `scc_c0_future_inextendibility`, no C0/C2 merge or strengthening | pass |
| C12 | no WCC/`I+`/visibility content in the conclusion | pass |
| C13 | genericity residual-comeager and declared part of the class | pass |
| C14 | falsifier refutes this class, non-meagerness route, machine-checkable steps | pass |
| C15 | one-way ledger C0=>H2loc=>C2 complete; C2=>class and WCC=>class forbidden; shared (s,delta) with F1/F2a | pass |

Two observations are recorded but **excluded from the accept's scope**:

- **OBS-089-2** — inline `f0_binding.consistency_evidence_sha256` (675a99d0) is stale: the live
  `artifacts/formulation/evidence/taxonomy_consistency.json` measures 9e335e9b, which FROZEN rev28
  pins. Same family-wide defect as HF-034-F2A-3 / HF-086-R1.
- **OBS-089-3** — measured input to the audit lead's **O-GFORM-1**: at rev12 the F2a/F2b
  `data_class` blocks have the same key set and differ only in `adm_mass` annotation text; the
  C0/C2 separation rests on `class_components.regularity_token` and `extension_predicate`
  (`C0`/`none` vs `C2`/`classical_ricci`). Not adjudicated here.

## Controls

M1 duplicate key · M2 future `revised_at` · M3 pointer redirected at the authoring tree ·
M4 dangling pointer fragment · M5 corrupted declared F0 hash · M6 authoring mirror divergence ·
M7 merge-shaped class id · M8 D0 regressed to an ill-typed pair · M9 extension regularity widened
to C2 · M10 WCC visibility predicate imported into the conclusion · M11 conclusion type widened to
C2 · M12 falsifier rebound to the sibling · M13 C0=>C2 entailment deleted · M14 genericity demoted
out of the class identity. All 14 are caught by their mapped check; the unmutated baseline passes
all 15 checks.

**Method note (CHECKER-NOTE-089-1):** three checker encodings were corrected while developing the
checker, before the frozen run — case-insensitive ambient-space test (`SUBSPACE topology`), the
`this class` token used for the C2=>class forbidden row, and the meager-complement wording of
`generic_set`. None weakens a substantive invariant; each corrected check retains its control.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-089/f2b_rev12_review/check_f2b_rev12.py --window 90 --interval 15
```

Reads shared artifacts read-only; writes only inside `artifacts/worker-089/f2b_rev12_review/`.
Snapshots: `pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml`, `pinned/FROZEN.rev28.json`.

## Falsifier

Any of C01–C15 flips to fail at a newer canonical hash of `schemas/af_scc_c0_vacuum.yaml`, or the
FROZEN pin/mirror equality breaks, or a planted control stops being caught — then this accept is
void for the newer revision. A hash move inside the stability window makes the verdict advisory
for the pinned bytes only.
