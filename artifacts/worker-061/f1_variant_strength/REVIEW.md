# W061-F1-VARSTRENGTH-05 — independent variant strictness-direction adjudication
- worker: worker-061
- created_at: 2026-09-12T00:53:46+08:00
- node: F1 (primary AF-WCC-VAC-GEN); F2b CH secondary (AF-SCC-C0-VAC-GEN)
- gate: G-FORM

## Verdict: **revise** (score 4.0)

## Hard failures
- HF-W061-VAR-01 (F1 SET predicate-level label inverted): schemas/af_wcc_vacuum.yaml:234 asserts variant SET is 'strictly STRONGER than this class's single-q tail predicate', but T => S holds unconditionally (finite corpus: 0 violations) and S => T fails on the omega chain (escape certificate). The single-q tail predicate is the strictly stronger reading; SET is strictly weaker. The same field's support clause ('non-containment in the union implies no single q sees a tail') is the correct negation-level implication not-S => not-T, i.e. it contradicts the predicate-level label.
- HF-W061-VAR-02 (SET delta self-contradiction): changes[visibility.definition].to says the SET predicate 'is implied by, and strictly stronger than, the single-q tail predicate' - the two conjuncts cannot both hold under any level convention.

## Findings
1. F-W061-VAR-01 (level indexing; repair guidance): the variant's NEGATION/CLASS-level label is correct and must NOT be flipped. Variant SET's negation (no SET-visible geodesic) is strictly stronger than the canonical negation (no tail-visible geodesic), because not-S => not-T (0 violations) and the omega chain has not-T true with not-S false. Registry strength (class target, 'strictly STRONGER than AF-WCC-VAC-GEN') is therefore consistent as written. A blanket inversion of every 'strictly STRONGER' token would repair the predicate-level label and break the class-level one.
2. F-W061-VAR-02 (worker-076 W076-GFORM-VIS-STRENGTH-03 corroboration): the blocker's direction is confirmed at the predicate level by an independent model corpus and an independent omega escape certificate; its scope is predicate-level. worker-076's 'line 215 forces the opposite direction' is reproduced: line 215 is correct and, by negation, forces T strictly stronger.
3. F-W061-VAR-03 (F2b CH positive control): schemas/af_scc_c0_vacuum.yaml:291 'strictly WEAKER than this frozen class' is consistent with broad => CH; E_CH subset E_all. The support clause is imprecise: a non-conditional refutation of CH does refute the broad class; the sentence is saved only by the word 'conditional', and 'it' has an ambiguous antecedent (same defect family as flash-19 F0-19-05). This is a soft precision finding, not an inversion; do not flip CH.
4. F-W061-VAR-04 (falsifier status): the record's falsifier (equivalence of the two readings) is REFUTED at the omega chain, so the falsifier does not fire; it supplies no support for either strength label. D1 remains a real divergence at the predicate level.
5. F-W061-VAR-05 (ESC-2 consequence): option (A) 'reconcile to one predicate' cannot be justified as 'the two readings are equivalent' - the omega chain refutes equivalence. Option (C) 'keep named variants' needs a two-level strength statement: the SET predicate is strictly weaker; the SET-variant negation is strictly stronger. Neither option is settled by this review; this review only fixes the direction at each level.
6. F-W061-VAR-06 (independence): this review did not read reviews/*F1*, reviews/*F2b* or any other reviewer's verdict before writing; it did read worker-076's blocker event and the adjudicated F0 review finding flash-19 F0-19-04/05 (used only as prior-art citations, not reused text). The probe re-implements the semantics from the pinned definitions; no worker-076 code was executed or copied.

## Machine checks
- finite corpus: 389 preorders, 154452 cases, T=>S violations 0, S=>T violations 0
- omega chain: S=True, T=False, escape certificate 3660 pairs all hold = True
- controls: 5 mutants, all detectors fired = True

## Pins
- `schemas/af_wcc_vacuum.yaml` = `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` (pin matches live: True)
- `schemas/af_scc_c0_vacuum.yaml` = `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` (pin matches live: True)
- `artifacts/formulation/VARIANT_REGISTRY.json` = `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` (pin matches live: True)
- `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json` = `45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc` (pin matches live: True)
- `artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json` = `c28795b0fdfc1c58cc3cd7519e0d0965cbf3c2ceb6171c5ffd346735189a2185` (pin matches live: True)
- `artifacts/formulation/FROZEN.json` = `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` (pin matches live: True)

## Falsifier
On the pins F1 cce9c60146d6 / F2b 55d0a1ea9bda / registry 5eb42f9a384a / SET delta 45b9b6a8d192 / CH delta c28795b0fdfc, this revise is falsified by any one of: (a) a proof that in every admissible asymptotically flat completion the family of witnessing points on I+ is down-directed (then S => T and the omega certificate is inadmissible, making the two readings equivalent); (b) a canonical convention, recorded elsewhere in the frozen corpus or by controller decision, under which 'X is strictly stronger than predicate P' means 'the negation of X is stronger than the negation of P' - under that convention F1:234 is consistent and only the delta's 'implied by, and strictly stronger than' remains a defect; (c) the labels being repaired to an explicit two-level statement, which resolves HF-01/02 without changing either direction.

## Authority
Worker evidence only. No gate verdict, node status or validation_status is claimed.
