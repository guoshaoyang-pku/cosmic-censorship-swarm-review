# W058-CONTAIN-DERIVE-04 — containment-derivation certificate for the frozen SCC pair

**Worker** `worker-058` (slot 058) · **node** F2b · **classes** `AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN`
· **gate context** G-FORM · read-only on every canonical path.

**Verdict: FAIL — 1 hard (`class_size_predicate_inverted`, C0:245), 1 advisory
(`stale_containment_denial`, C0:151); all 3 containment links DERIVED (3/3) from the frozen
definitional base.**

This is the task the three prior W058 audits pre-registered as their carried limitation:
`W058-CONTAIN-01/02/03` took the declared containment chain as an **axiom**. This certificate
re-derives the chain from the frozen definitional base, records the warrant of every link, and
sweeps the bound bytes for size/strength assertions that contradict the derived order.

## Binding (measured at run time; verdicts bind to sha256, never to a revision number)

| input | path | sha256 |
|---|---|---|
| C0 schema | `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| C2 schema | `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| variant registry | `artifacts/formulation/VARIANT_REGISTRY.json` | `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` |
| declared F0 taxonomy | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| frozen manifest | `artifacts/formulation/FROZEN.json` | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` (rev 28) |

`frozen_pin_drift = []` for all four pinned inputs (`frozen_match: true`).

## 1. The chain is derivable — with one definitional dependency

Canonical order (smallest extension set first):

```
E_C2  ⊂  E_{C^1,1}  ⊂  E_H2loc  ⊂  E_C0
```

Both schemas declare it: C0:238 descending (`E_C0 contains … contains E_C2`) and C2:236
ascending (`E_C2 subset of … subset of E_C0`). Cross-file agreement: **yes** after direction
normalisation. Prose occurrences at C2:147 and C2:151 also carry the canonical chain.

| link | statement | rules | status | warrant / dependency |
|---|---|---|---|---|
| L1 | `E_C2 ⊂ E_{C^1,1}` | R1 | **derived** | C2 ⟹ C^{1,1} (derivative count); same base extension predicate |
| L2 | `E_{C^1,1} ⊂ E_H2loc` | R2, R4, R3 | **derived** | C^{1,1} ⟹ Riem ∈ L∞_loc ⊂ L2_loc (R2) and C^{1,1} ⟹ C0 (R4), satisfying both conjuncts of the H2LOC definition (R3) |
| L3 | `E_H2loc ⊂ E_C0` | R3 | **derived** | H2LOC membership is *defined* as "continuous metric **with** Riemann tensor in L^2_loc"; continuity is a defining conjunct. |

**Definitional dependency (new, and the reason this task existed):** L3 is not a theorem about
curvature; it is exact only under the registered H2LOC definition, which carries metric
continuity as a conjunct. A curvature-only reading of `H2_loc` would **not** give
`E_H2loc ⊂ E_C0` in 4D: `H^2_loc` does not embed into `C^0` at the sharp Sobolev borderline
`s = n/2 = 2`. Mutant `M4_h2loc_continuity_stripped` strips the conjunct and the checker flips L3
to `under_justified` — the sensitivity is demonstrated, not asserted.

This resolves the tension that the earlier sweep filed as an advisory: C0:99/C0:151 call H2_loc
"not C0" / "phrased in terms of CURVATURE"; that is compatible with the registry only because the
registry adds continuity. C0:151's outright denial ("No containment with C2 or C0 is asserted
here") is stale against both the ledger and the registry and is reported as an advisory.

## 2. Findings at the bound bytes

| id | code | severity | where | quote (abridged) | repair |
|---|---|---|---|---|---|
| W058-CD-F1 | `class_size_predicate_inverted` | **hard** | C0:245 (`implication_ledger.forbidden_transfers[0].reason`) | "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker" | one word: `larger` → `smaller` |
| W058-CD-F2 | `stale_containment_denial` | advisory | C0:151 (`regularity.must_not_conflate[0]`) | "No containment with C2 or C0 is asserted here" | scope the denial to the definition block or point at `implication_ledger` |

W058-CD-F1 is the same defect recorded by worker-08 at `a8d899d2`, independently confirmed by
W058-CONTAIN-01 at `1bb78ce9` and W058-REV27-CERT-03 at `55d0a1ea`; this certificate adds its
*warrant*: the derived order makes `smaller` the only licensed word. The transfer direction and
the consequent ("C2-inextendibility is strictly weaker") are correct; only the class-size
antecedent is false.

23 checks are consistent, including every `E_X subset E_Y` assertion in both ledgers, every
strength label on the entailment rows, both chain declarations, and the repaired F0 vocabulary
entry `field_vocabulary.regularity_token.meaning_C2` ("It does NOT forbid C^{1,1} or H^2_loc
extensions: those are strictly larger classes") — which now agrees with the SCC-derived order.

## 3. Pre-registered acceptance test

- **repair A:** C0:245 `strictly larger` → `strictly smaller`;
- **repair B:** scope/replace the C0:151 denial (this checker's only advisory);
- after both repairs at a new frozen C0 hash, the **unmodified** checker must return `PASS`
  (`hard = 0`, `advisory = 0`) with all three links still `derived`.

Mutant `M1_both_repairs` demonstrates exactly this. `M1a_inversion_only` shows the intermediate
state (PASS with the denial still advisory); `M1b_denial_only` shows repair B alone leaves the
hard finding.

## 4. Calibration — 12/12 mutant expectations met

`run_sensitivity_selftest.py` stages 12 trees under `_scratch/` and runs the unmodified checker
on each:

| case | expected | observed |
|---|---|---|
| CANON canonical bytes | FAIL, hard `class_size_predicate_inverted`, adv `stale_containment_denial`, 3/3 links | met |
| CTRL byte-identical copy | identical verdict to canonical | met |
| **M1 both repairs** | **PASS, hard 0, adv 0, 3/3 links** | met |
| M1a inversion-only | PASS, adv `stale_containment_denial` | met |
| M1b denial-only | FAIL, hard `class_size_predicate_inverted` | met |
| M2 C0 chain reordered | `chain_declaration_not_canonical` | met |
| M3 C2 structured chain reversed | `chain_declaration_not_canonical` + `subset_assertion_reversed` | met |
| **M4 H2LOC continuity conjunct stripped** | **L3 `under_justified` + `containment_link_under_justified`** | met |
| M5 fresh inversion planted in C2 | `class_size_predicate_inverted` | met |
| M6 F0 vocabulary regression | `f0_meaning_C2_claims_larger_classes_forbidden` | met |
| M7 FROZEN pin altered (flag off / on) | `frozen_pin_drift` only when required | met |

## 5. Falsifier

A reader exhibits (a) a frozen definitional base in which a chain link fails or the order
reverses; (b) the checker returning PASS while a bound sentence still calls C2 strictly larger or
denies containment; (c) a mutant above that the checker reports with the canonical verdict; or
(d) VARIANT_REGISTRY H2LOC losing the continuity conjunct while L3 is still reported `derived`.

**Next falsifier:** re-run at the next canonical C0/C2/registry hashes. Falsified if the derived
order changes, if L3 becomes under-justified with the continuity conjunct still present, or if
the hard finding disappears without repair A.

## 6. Boundary

Artifact-consistency and definitional-derivation audit only. The rule base R1–R4 is declared and
sourced; the checker verifies closure of the chain under it and the presence of each warrant in
the bound bytes — it does not prove the calculus rules. The sweep is lexical/semi-structured over
sentences carrying class tokens and comparator tokens. No mathematical truth claim about
asymptotic censorship, no citation scope, no node completion, no gate verdict. The worker claims
none of those; `astra-lead-formulation` owns the repairs and any gate consequence.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-058/contain_derive/derive_containment.py --root . \
    --out artifacts/worker-058/contain_derive/containment_derivation.json
python3 artifacts/worker-058/contain_derive/run_sensitivity_selftest.py
```

Checker exit codes: `0` = PASS (no hard findings), `1` = FAIL (hard findings), `2` = input error.
