# W027-SET-STRENGTH-CONVENTION-01 — SET strength: predicate vs class conclusion

**Worker:** worker-027 · **Node:** F1 (touches F0) · **Gate:** G-FORM (evidence also relevant to G-F0)
**Class:** AF-WCC-VAC-GEN
**Verdict:** `SET_STRENGTH_CONVENTION_CONFLICT_CONFIRMED` (exit 0)
**Report:** `report.json` · **Instrument:** `verify_set_strength.py` · **Pins:** `pinned/MANIFEST.json`

## One-paragraph answer

At FROZEN rev29 the SET variant of `AF-WCC-VAC-GEN` is **strictly STRONGER than its parent as a class
conclusion**, while the union visibility predicate is **strictly WEAKER than the single-q tail
predicate**. Both facts are machine-checked here (exhaustive finite preorders + an explicit
omega-chain witness). The rev13 repair correctly fixed the F1 *predicate* wording, but it also flipped
the two *class-strength* fields (`VARIANT_REGISTRY.json` SET `strength`, and the SET delta `strength`)
to "strictly weaker", which is false under the registry's own convention (all six sibling variants name
class relata). The result is an internally contradictory live corpus and a **false pass of the frozen
variant-registry checker**, which still requires SET to be marked stronger but is satisfied by the
quoted old token inside the rev13 annotation. The F0 artifacts that blocker L-FORM-03 calls "inverted"
are **correct under the class convention**; reopening or re-labelling F0 on this evidence would
introduce an error. The repair belongs in the two rev13 strength tokens (plus a level-naming edit in the
F1 relation string).

## The two levels, kept apart

| statement | relatum | truth | machine evidence |
|---|---|---|---|
| `P_tail(g) ⇒ P_set(g)` (single-q tail ⊆ union) | visibility predicate | holds, 0/45358 violations | `checks.T2a` |
| union reading vs single-q predicate | visibility predicate | union is **strictly weaker** | omega witness (`T4`) |
| `C_SET ⇒ C_PARENT` (`¬P_set ⇒ ¬P_tail`) | class conclusion | holds, 0/5541 models | `checks.T3` |
| SET variant vs parent class | class conclusion | SET is **strictly STRONGER** | omega model M0 (`T4_M0_*`) |

The exhaustive sweep covers all reflexive-transitive relations on ≤4 points, all non-empty I⁺ subsets
and all strict chains: 5541 models / 45358 geodesics. For **finite** chains the two readings collapse
(0 separations, `T2b`/`T3b`), which is why the 0/355-preorder result alone cannot settle a strength
label; the separation needs the infinite omega-chain (`x_i ≤ q_j ⇔ i ≤ j`), where
`P_set(gamma)=true`, `P_tail(gamma)=false`.

## Token audit (see `report.json.tokens`)

| token | relatum named | direction | true? |
|---|---|---|---|
| F0 canonical `research_map/formulation_taxonomy.yaml:200` ("The set-based reading … is strictly stronger") | class/variant (registered variant) | stronger | **true** |
| F0 supplement D1 `artifacts/formulation/formulation_taxonomy.yaml:176` ("F0 was stronger; (b) implies (c) but not conversely") | class conclusion | stronger | **true** (`(b)⇒(c)` is the contrapositive of `P_tail⇒P_set`) |
| F1 rev13 `schemas/af_wcc_vacuum.yaml:235` ("strictly WEAKER than this class's single-q tail predicate") | visibility predicate | weaker | **true as written** (but the sentence's justification is class-level) |
| F1 rev13 `schemas/af_wcc_vacuum.yaml:216` ("B-containment is strictly stronger") | class conclusion | stronger | **true** |
| `VARIANT_REGISTRY.json:57` SET `strength` ("strictly weaker than AF-WCC-VAC-GEN …") | class | weaker | **FALSE** |
| `AF-WCC-VAC-GEN.variant-SET.delta.json:11` `strength` | class | weaker | **FALSE** |
| same delta, `changes[visibility.negation_conclusion].to` ("strictly stronger than the single-q negation") | class | stronger | **true** (contradicts the line above it) |
| rev12 oracles (registry `5eb42f9a384a`, delta `45b9b6a8d192`, F1 `cce9c60146d6`) | class for registry/delta; predicate for F1 | stronger (class) / stronger (predicate) | registry+delta **true**; F1 predicate token **false** — the exact token the rev13 edit was entitled to fix |

So the live false-token set is exactly
`{registry_rev13:SET_strength, delta_rev13:strength, F1_rev12:variant_relation_oracle}`; the third is
historical and shows the repair's legitimate target. `report.json.false_tokens` equals the
pre-registered expectation.

## The frozen checker false-passes

`artifacts/formulation/tools/check_variant_registry.py` (pinned rev29, sha `c471da4b7be9`) contains at
its line 90:

```python
setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
if "STRONGER" not in setv.get("strength", ""):
    errs.append("variant SET must be marked stronger than its parent")
```

The live registry string is `"strictly weaker than … [rev13 direction corrected from 'strictly
STRONGER']"` — the substring test finds `STRONGER` inside the annotation. Executed in a private sandbox
(only copies written):

| sandbox registry | frozen checker exit | output |
|---|---|---|
| live rev13 bytes | **0** | `VALID: 4 parent classes, 7 variants` |
| annotation stripped | **1** | `variant SET must be marked stronger than its parent` |
| leading token corrected to `strictly STRONGER` | 0 | `VALID` |

Provenance: the rev13 rebase tool `artifacts/formulation/tools/variant_rebase_rev29.py`
(sha `e9521823b8bb`) sets `STRENGTH_NEW = "strictly weaker than AF-WCC-VAC-GEN …"` and never references
`check_variant_registry`. The token was flipped against the frozen checker's rule, and the checker's
substring test hid it. `check_variant_registry VALID` at rev29 is therefore **not** evidence about the
strength direction.

## Consequence for blocker L-FORM-03

L-FORM-03(a) (`F0:200 'strictly stronger'`) and (b) (supplement D1 `relation`) are **referent errors**:
they compare class conclusions, where "stronger" is true. They do not contradict the corrected F1
*predicate* sentence at line 235; the two sentences are about different relata. The measured live defect
is instead the two rev13 class-strength tokens (and the un-named level in F1 line 235).
`proposed_erratum.md` gives minimal unapplied patches. Because F0 canonical `0abb9ed8a961` and the
supplement `d7419b4e8963` are frozen by REC-11, no F0 write is needed for this item.

## Reproduction and falsifier

```bash
python3 artifacts/worker-027/set_strength_convention/verify_set_strength.py   # exit 0/2/3
```

Falsified if any pinned sha differs at entry or exit (exit 2); a finite model has `P_tail ∧ ¬P_set`; the
omega witness is non-transitive, fails `P_set`, or some `q_j` dominates a tail of gamma; any model has
`C_SET ∧ ¬C_PARENT`; M0 fails; the annotation-stripped copy still exits 0 or the corrected copy exits
non-zero; the six sibling variants do not name class relata; or a frozen consumer names a predicate in
the leading clause of the SET strength token. Full text in `report.json.falsifier`.

## Non-claims

Worker-level measurement only: no gate verdict, node status, or `validation_status`; no canonical file
modified (sandbox runs use private copies); the model checks the order-theoretic content of the
predicates, not a Lorentzian realization; no claim about the physics of cosmic censorship.
