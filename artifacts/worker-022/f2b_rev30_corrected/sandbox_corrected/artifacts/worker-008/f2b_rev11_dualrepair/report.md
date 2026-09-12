# W008-F2B-DUALREPAIR-01 — F2b containment-consistency repair readiness

- canonical C0 `schemas/af_scc_c0_vacuum.yaml` @ `1bb78ce9b357` (FROZEN rev 26, inside the frozen set: True)
- canonical C2 `schemas/af_scc_c2_vacuum.yaml` @ `b6123750b37d`
- canonical audit: **FAIL** — false_containment_denial, size_premise_inverted
- candidate audit: **PASS** (candidate sha256 `b21153b123b7`)
- minimality: **PASS** — changed leaf paths ['implication_ledger.forbidden_transfers[0].reason', 'regularity.must_not_conflate[0]']
- controls: **all met** (ctl1 reverted D2 -> size_premise_inverted; ctl2 reverted D1 -> false_containment_denial)
- checker selftest: **ok** (6/6 synthetic cases)

## Findings (canonical, hash-bound)

1. `implication_ledger.forbidden_transfers[0].reason` (line 251): class-size premise inverted (`larger` -> `smaller`); transfer direction and strength consequent unchanged.
2. `regularity.must_not_conflate[0]` (line 157): false containment denial; the sibling C2 schema already carries the corrected wording.

## Scope

Textual/logical consistency audit only; no gate verdict, no node completion, no claim about the truth of the class. Owner applies the two-line repair and re-freezes.

Falsifier: Exhibit a reading under which line 251's 'C2 is a strictly larger extension class' is not a class-size premise, or a reading under which line 157's denial is consistent with the same file's chain; or measure a canonical C0 hash different from the bound one and show the two findings absent there; or show a candidate structural change outside the two declared leaf paths. Any of these falsifies this report at the bound hashes.
