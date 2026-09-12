# Proposed erratum — SET strength tokens at FROZEN rev29 (UNAPPLIED)

Owner of the canonical files: formulation lead. This worker does not edit canonical bytes (and F0 is
frozen by REC-11). Each patch below is minimal, keeps every class id / hypothesis / conclusion predicate
/ genericity value unchanged, and is stated so that the frozen checker's own rule ("variant SET must be
marked stronger than its parent", `check_variant_registry.py:90`) is satisfied **by the true token**, not
by an annotation.

Truth that the patches encode (machine-checked in `report.json`):

- visibility-predicate level: `P_tail ⇒ P_set`; the union reading is **strictly weaker**;
- class-conclusion level: `¬P_set ⇒ ¬P_tail`; the SET variant is **strictly STRONGER** than
  `AF-WCC-VAC-GEN`, and the entailment is strict (omega-chain).

---

## P1 — `artifacts/formulation/VARIANT_REGISTRY.json:57` (SET `strength`)

Current (sha `6bac9adea19e`):

```json
"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent's single-q tail predicate entails the union reading; the converse fails on the omega-chain witness, W076-GFORM-STRICTNESS-RECONCILE-06 T4): gamma not contained in the union J^-(I+) implies no single past J^-(q) contains a tail of gamma, but not conversely [rev13 direction corrected from 'strictly STRONGER']",
```

Proposed:

```json
"strength": "strictly STRONGER than AF-WCC-VAC-GEN as a class conclusion: gamma not contained in the union J^-(I+) implies no single past J^-(q) contains a tail of gamma, but not conversely (the omega-chain witness W076-GFORM-STRICTNESS-RECONCILE-06 T4 separates them). The opposite direction holds only at the visibility-predicate level: the union reading is strictly WEAKER than the single-q tail predicate, which entails it. [rev13 token corrected to the class level; the predicate-level 'weaker' belongs to the F1 variant relation field]",
```

## P2 — `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json:11` (`strength`)

Current (sha `64b8d6394a04`):

```json
"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent's single-q tail predicate entails the union reading; the converse fails on the omega-chain witness, W076-GFORM-STRICTNESS-RECONCILE-06 T4)",
```

Proposed:

```json
"strength": "strictly STRONGER than AF-WCC-VAC-GEN as a class conclusion (its negation entails the parent's negation, not conversely; W076-GFORM-STRICTNESS-RECONCILE-06 T4). The union visibility predicate is strictly WEAKER than the single-q tail predicate; the two levels must not be interchanged.",
```

This makes the `strength` field agree with the same file's `changes[visibility.negation_conclusion].to`
("This is strictly stronger than the single-q negation") and with `schemas/af_wcc_vacuum.yaml:216`
("B-containment is strictly stronger").

## P3 — `schemas/af_wcc_vacuum.yaml:235` (F1 variant `relation`; level-naming only)

Current (sha `d9cebb9404b2`):

```yaml
    relation: "strictly WEAKER than this class's single-q tail predicate: the single-q tail predicate entails the union reading, and non-containment in the union implies no single q sees a tail of gamma, but not conversely; the two readings are NOT equivalent and must never be interchanged. [rev13: ...]"
```

Proposed:

```yaml
    relation: "VISIBILITY-PREDICATE level: the union reading is strictly WEAKER than this class's single-q tail predicate (the tail predicate entails the union reading, not conversely). CLASS-CONCLUSION level: the SET variant is strictly STRONGER than this class (non-containment in the union implies no single q sees a tail of gamma, not conversely). The two readings are NOT equivalent and must never be interchanged. [rev13: predicate direction corrected from 'strictly STRONGER'; the class-level direction is 'stronger' - W076-GFORM-STRICTNESS-RECONCILE-06 T2/T3/T4]"
```

## P4 — F0 artifacts: **no write now** (REC-11 freeze)

`research_map/formulation_taxonomy.yaml:200` ("The set-based reading … is strictly stronger") and
`artifacts/formulation/formulation_taxonomy.yaml:176` (D1 `relation: "F0 was stronger; (b) implies (c)
but not conversely"`) are **true under the class-conclusion convention**. They should not be flipped.
If a future revision touches these bytes for other reasons, the editorial addition
"(as a class conclusion; the union visibility predicate is strictly weaker)" removes the ambiguity at
zero semantic cost. Blocker L-FORM-03(a)/(b) can be closed as a referent error on this evidence;
L-FORM-03 should be re-scoped to the P1/P2 tokens.

---

## Checker hardening (audit-lead-owned, recommended, not covered by P1–P3)

`check_variant_registry.py:90` tests `"STRONGER" in strength`, so any annotation quoting the old token
satisfies it (measured: annotation-stripped copy → exit 1; live copy → exit 0). Test the leading clause
instead, e.g. `re.match(r"\s*strictly\s+STRONGER\b", strength)` or `strength.split("[")[0]`. The tool is
pinned at `c471da4b7be9` in rev29, so this is a rev30 item.

## Consequences and acceptance criteria

- P1/P2 move two pinned rev29 artifacts (`VARIANT_REGISTRY.json`, SET delta) and require a rev30
  manifest plus re-review; P3 moves `schemas/af_wcc_vacuum.yaml` and voids rev13 F1 verdicts at
  `d9cebb9404b2`. F0 canonical `0abb9ed8a961` and supplement `d7419b4e8963` are untouched by all four.
- Acceptance: after P1+P2, (i) the frozen checker still exits 0, now on the leading token; (ii) the
  registry/delta `strength` agrees with their own negation clauses; (iii) a reviewer at the new hashes
  finds both levels named and no class-id/hypothesis/conclusion-predicate/genericity change.
- Risk of not fixing: any future class-strength reasoning reads "SET is weaker than its parent", and the
  frozen checker's rule stays unenforced by a substring artifact.
