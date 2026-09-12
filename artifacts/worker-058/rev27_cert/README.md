# W058-REV27-CERT-03 — rev12-delta certificate for the frozen SCC pair

**Worker** `worker-058` (slot 058) · **node** F2b · **classes** `AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN`
· **gate context** G-FORM · read-only on canonical bytes.

**Verdict: FAIL — the two recorded C0 repairs are still pending at the new frozen hash; the four rev12
close-findings claims are independently verified; rev12 introduced no new order/strength finding.**

This is the successor task that `W058-REPAIR-CERT-02` pre-registered as its `next_falsifier` ("re-run at
the next canonical C0 hash"). It answers both halves of that pre-registration: (a) the unmodified
acceptance checker at the post-rev12 hash, and (b) an independent re-measurement of what the rev12 edit
actually closed.

## Binding (measured at run time; verdicts bind to sha256, never to a revision number)

| input | path | sha256 |
|---|---|---|
| C0 schema | `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| C2 schema | `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| manifest | `artifacts/formulation/FROZEN.json` | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` (revision 28) |
| acceptance checker | `artifacts/worker-058/rev27_cert/sweep_scc_order_frozen_copy.py` | `ff4fba42f4f07d9a056f2edfa687824815c056daf79ae2498fc4a1f6233c7bf3` |
| rev26 baseline snapshot | `artifacts/worker-058/repair_cert/_scratch/M0_canonical/` | C0 `1bb78ce9…`, C2 `b6123750…` |

**Manifest motion during the task:** `FROZEN.json` moved rev27 (00:32:59) → rev28 (00:35:08). The SCC pin
bytes were unchanged at every measurement (`frozen_match: true` for both files). The certificate records
the manifest sha it last measured and treats the revision number as advisory.

## 1. Pre-registered acceptance test at rev27 — still FAIL

`sweep_scc_order_frozen_copy.py --root .` (byte-identical to the tool recorded in the
W058-REPAIR-CERT-02 events) evaluates 40 order/strength claims and returns:

| | rev26 baseline (`1bb78ce9`/`b6123750`) | rev27 (`55d0a1ea`/`5476a3f2`) |
|---|---|---|
| verdict | FAIL | **FAIL** |
| hard | 2 | **2** |
| advisory | 3 | 3 |
| consistent | 35 | 35 |
| duplicate-key entries (tool) | 14 (double-count quirk) | 0 |
| duplicate keys (node-level, this cert) | 7 in C0, 7 in C2 | **0 in both** |

Hard findings, persisting unchanged in code and class, shifted by −6 lines because the rev12 edit
collapsed the repeated `revised_at:` keys into `revision_history`:

- **HF-1 `class_size_predicate_inverted`** — `C0:245` (was `:251`): `implication_ledger.forbidden_transfers[0].reason`
  says *"C2 is a strictly larger extension class"*, contradicting the chain the same file declares
  (`E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`). Transfer direction and consequent are correct; only the
  antecedent is false. One-word repair: `larger` → `smaller`.
- **MINOR-1 `strength_bucket_mismatch`** — `C0:234` (was `:240`): *"replacing future by two-sided
  direction"* is still filed under `conclusion.forbidden_weakenings` although two-sided is strictly
  stronger (the file itself says so at `C0:225`, where the item also already appears under
  `forbidden_strengthenings`). Repair: drop the duplicate from `forbidden_weakenings`.

`delta.new_hard_codes = []`, `delta.resolved_hard_codes = []`. rev12 neither introduced nor repaired any
order/strength hard finding.

## 2. rev12 close-findings claims — all four independently verified

| claim (`astra-life03-close-findings`) | check | result |
|---|---|---|
| C1 duplicate `revised_at:` keys collapsed into `revision_history` | node-level duplicate-key walk on both files | **verified** — rev26 had 7 duplicate keys in C0 and 7 in C2; rev27 has 0 in both |
| C2 `revised_at` stamped with wall clock | future-dating scan over `revised_at` + every `revision_history[*].at` (120 s tolerance) | **verified** — max stamp `2026-09-12T00:31:41+08:00`, not future-dated; `revised_at` = newest history entry |
| C3 `class_contract_pointer` repointed at taxonomy key `classes`, supplement split out | fragment resolution against both taxonomy files on disk, plus every `quantifiers.domains.*.definition_ref` | **verified** — all four pointers resolve (C0/C2 canonical + supplement) |
| C4 D0 retyped from pair `(s,delta)` to tagged index `r` | stale pair-binder scan of all lines outside the D0 definition | **verified** — 0 stale binders in rev27; the rev26 baseline C0 does contain `forall (s,delta) in D0` and is caught |

Structure checks: `revision_history` indices contiguous 1..10, top-level `revision 12 ≥ max index`, at
least one published entry; no duplicate indices.

## 3. Calibration — 10/10 mutant expectations met

`run_sensitivity_selftest.py` builds eight trees under `_scratch/` and runs the certificate on each:

| case | expected | observed |
|---|---|---|
| checker identity | frozen sweep copy sha == `ff4fba42…` | met |
| CANONICAL rev27 | `D6_HF1_open`, `D6_MINOR1_open` | met |
| CTRL byte-identical copy | same hard set as canonical | met |
| MUT duplicate key planted | `C1_duplicate_keys` | met |
| MUT future `revised_at` planted | `C2_wall_clock` | met |
| MUT dangling `class_contract_pointer` | `C3_pointer` | met |
| MUT rev26-style `forall (s,delta)` binder | `C4_stale_pair_binder` | met |
| **MUT both repairs applied** | **zero hard checks; sweep PASS** | **met** |
| MUT `FROZEN` pin altered | `D5_frozen_pin` | met |
| BASE rev26 snapshot | `C1`, `C4`, both repairs open | met |

The both-repairs mutant is the pre-registered acceptance demonstration: applying exactly the two
mechanical C0 repairs makes the unmodified checker return `hard = 0`.

## 4. Falsifier

A reader exhibits (a) a rev12 claim C1–C4 that is false at the bound bytes, (b) a stale pair-typed
regularity binder or dangling pointer this checker misses, (c) an order/strength hard finding present at
rev26 but absent from this certificate, or (d) a new rev27 defect that the calibrated mutants show the
checker would have caught but did not.

**Next falsifier:** re-run after the two C0 repairs land. Falsified if the unmodified sweep still returns
`hard > 0` at the new hash, or if the new hash re-introduces a C1–C4 class of defect.

## 5. Boundary

Audits internal artifact consistency only: no physical truth, no citation scope, no mathematical
correctness, no F1/WCC rev12 change (visibility clause, `AF_{I+}`), no F0 taxonomy, no C0/C2 class-merge.
The worker claims no node completion and no gate verdict — `astra-lead-formulation` owns the repairs and
any gate consequence.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-058/rev27_cert/check_rev12_delta.py --root . --out /tmp/cert.json
python3 artifacts/worker-058/rev27_cert/sweep_scc_order_frozen_copy.py --root . --out /tmp/sweep.json
python3 artifacts/worker-058/rev27_cert/run_sensitivity_selftest.py
```
