# R2 adversarial review — separation and internal consistency of the two SCC vacuum schemas

- Reviewer: R2 (independent adversarial reviewer)
- Date: 2026-09-11T23:44+08:00
- Targets (revision 5, verified against these hashes at review time):
  - `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` — `revision: 5`, md5 `9b3611acb5e1c270746dec6d5f8d8977`
  - `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` — `revision: 5`, md5 `94d3e714634db7fb37377bb590906ac8`
- Context read (not modified): `artifacts/formulation/rule_spec.json` (spec_version 1.2, md5 `6d088e1fd8312a30c95e5a3c402acf66`), `artifacts/formulation/formulation_taxonomy.yaml` (md5 `2eb6d9d4ccd5a4deebe1deded97f3987`), `artifacts/formulation/tools/check_class_schema.py`
- Gate run (reproduced on rev5): `python3 artifacts/formulation/tools/check_class_schema.py <schema>` → `PASS`, exit 0, `failed_rules=[]` on both files.
- Verdict: **revise**; score **2 / 5**.
- Explicit claim: **I claim no physics truth; I reviewed specification structure, separation, and internal consistency.**

Revision note (moving target): both targets were `revision: 1` at session start; they were rewritten to rev4 at 23:34:10 and to **rev5** at 23:37:51 by concurrent swarm repairs (the rev5 comment says "R1 review corrections (falsifier logic, visibility equivalence, genericity well-definedness, transfer witnesses)"). All findings below were re-verified against **rev5**. One defect I identified in rev4 and would have filed — the invalid tier_1 refutation route R1 ("exhibit a datum in the declared G and this refutes outright") — was independently found by R1 and is **repaired in rev5**; it is recorded in §10, not as an open finding. Three stale fields remain from the rev4 smooth-category repair (R2-04) and three genericity defects remain from rev4 (R2-16, R2-17).

---

## 1. SEPARATION (task item 1)

### 1.1 Clause-by-clause result

C2 `#extension_predicate.definition` vs C0 `#extension_predicate.definition`:

| clause | C2 (rev5) | C0 (rev5) | verdict |
|---|---|---|---|
| (a) | "iota: M -> M' is an isometric embedding (iota_* g = g' restricted to iota(M))" | identical text | under-specified in both (R2-04 residual: iota's regularity is not frozen) |
| (b) | "iota(M) is an open, proper subset of M'" | identical | OK |
| (c) | "M' is connected and time-orientable, and its time orientation restricts to that of M" | "M' is a SMOOTH (C-infinity) connected 4-manifold, time-orientable, whose time orientation restricts to that of M; the smooth structure is the category in which the metric is a tensor field, while the metric itself is only continuous" | OK for separation (background category only), but stale fields contradict it (R2-04) |
| (d) | "g' is a C2 Lorentzian metric (signature (-,+,+,+), nondegenerate) on M'" | "g' is a continuous, nondegenerate Lorentzian metric on M' (signature (-,+,+,+))" | **clean** |
| (e) | "Ric(g') = 0 holds classically at every point of M' (g' of class C2 makes Ric continuous, so this is a pointwise statement)" | "NO equation is required of g' on M'" | **clean** |
| (f) | identical future-point clause | identical future-point clause | intended (direction frozen the same); precision defect R2-05 |

`#regularity.extension_regularity` (`C2` vs `C0`), `#extension_regularity_exact` ("twice continuously differentiable metric; NOT C^{1,1}, NOT C1, NOT C0, NOT H2_loc, NOT smooth-only" vs "continuous (C0) nondegenerate Lorentzian metric; no differentiability assumed"), `#extension_solution_concept` / `#extension_predicate.frozen_equation_concept` (`classical_ricci` vs `none`), and `#extension_predicate.frozen_regularity` (`C2` vs `C0`) are all consistent with `#class_components.regularity_token` and `#class_id`.

### 1.2 Result: NO FINDING on the literal separation question

- No field of the C2 schema, read literally, admits a merely continuous extension: (d) requires C2, `#extension_regularity_exact` excludes C0, (e) requires classical Ric = 0, and `#regularity.must_not_conflate[1]` now separates the H2_loc curvature axis from metric differentiability.
- No field of the C0 schema requires differentiability of `g'`: (d) says continuous and (e) says no equation; the clause (c) smoothness is explicitly about the background manifold, not the metric.
- Conclusion types, class ids, node ids, anti_scope lists and tier_1 witnesses are class-specific; the gate passes R02/R06/R12/R13.
- Residual separation risks are all in prose or predicate precision: R2-04 (iota regularity; stale C0 category fields), R2-05 (clause (f)), R2-06 (object-vs-statement H2_loc wording).

---

## 2. IMPLICATION LEDGER (task item 2)

### 2.1 Claim (i): "no C0 extension entails no C2 extension" — VERIFIED with a caveat

`af_scc_c2_vacuum.yaml#implication_ledger.one_way_entailments[0]` and `af_scc_c0_vacuum.yaml#implication_ledger.one_way_entailments[0]`:
> `{from: "no proper future C0 extension", to: "no proper future C2 extension", relation: entails, reason: "every C2 extension is a C0 extension (extension-class containment); so C0-inextendibility is the stronger statement", status: elementary}`

Correct. E_C2 ⊆ E_C0: a C2 metric is continuous and nondegenerate, and the C0 clause (e) imposes no equation, so the extra classical-Ric constraint only shrinks the C2 side. The **equation-requirement axis is on the correct side** of the containment. Caveat: the containment premise is only fully checkable once clause (a)'s `iota_* g` and iota's regularity are frozen (R2-04).

### 2.2 Claim (ii): the converse is forbidden — VERIFIED

`af_scc_c2_vacuum.yaml#implication_ledger.forbidden_transfers[0]` ("the converse containment is false") and `af_scc_c0_vacuum.yaml#implication_ledger.forbidden_transfers[0]` ("C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker than C0-inextendibility"). Correct: continuous non-C2 Lorentzian metrics exist, so E_C0 ⊋ E_C2.

### 2.3 Claim (iii): bare-metric C0 inextendibility entails distributional-vacuum C0 inextendibility — VERIFIED CONDITIONAL

`af_scc_c0_vacuum.yaml#implication_ledger.one_way_entailments[1]`:
> `{from: "no proper future C0 metric extension", to: "no proper future C0 distributional-vacuum extension", relation: entails, reason: "extensions required to solve Ric = 0 distributionally are a subset of all continuous metric extensions", status: elementary}`

Correct if the variant means "continuous metric with Ric = 0 distributionally" (then E_dist ⊆ E_bare). Conditional because the variant has no frozen predicate anywhere in the artifact, and the natural minimal setting for distributional Ricci is g ∈ H^1_loc ∩ L^∞_loc rather than literally C0 (R2-09).

### 2.4 The H2_loc entry is WRONG (R2-03, unrepaired)

`af_scc_c2_vacuum.yaml#implication_ledger.forbidden_transfers[1]`:
> `{from: "H2_loc-inextendibility", to: "this class", reason: "H2_loc is a distinct value on the regularity axis"}`

and in the same file `#regularity.must_not_conflate[1]`:
> "C^{1,1} and H2_loc extension classes are NOT this class; H2_loc is a curvature-regularity axis value, not a metric differentiability class, and **no containment with C2 is asserted**"

Every C2 metric has continuous second derivatives, hence is locally H^2 with locally bounded (hence L^2_loc) curvature; a C2 vacuum extension also satisfies Ric = 0 distributionally. Therefore E_C2 ⊆ E_H2loc under both plausible readings ("H^2_loc metric" or "curvature ∈ L^2_loc"), so H2_loc-inextendibility **does entail** C2-inextendibility and the forbidden transfer is mathematically false. "No containment with C2 is asserted" cannot coexist with a ledger entry that forbids the transfer, because forbidding requires E_C2 ⊄ E_H2loc.

The taxonomy carries the same error: `formulation_taxonomy.yaml#implication_ledger` records `{from: "H2_loc inextendibility", to: "AF-SCC-C2-VAC-GEN", relation: does_not_entail, ...}`; `#axis_registry.regularity_axis.containment` says "C2 subset C0 as classes of extensions; H2_loc is incomparable with C2 and strictly inside the C0-metric class in the relevant sense" (self-contradictory: C2 ⊆ H2_loc under either reading; and under the literal "H^2_loc metric" reading H^2_loc(R^4) ⊄ C^0 because the Sobolev embedding is borderline, k = n/p = 2); and `#class_contracts.AF-SCC-C0-VAC-GEN.negative_test_case.reason` still says "H^2_loc is strictly between C2 and C0".

The C0 file's parallel forbidden transfer (`#implication_ledger.forbidden_transfers[1]`: "... not contained in this class's extension set in the needed direction") is **correct** as a statement-direction claim (E_C0 ⊄ E_H2loc, so H2_loc-inextendibility does not give C0-inextendibility). But the C0 ledger then omits the valid implication C0-inextendibility ⇒ H2_loc-inextendibility that follows from the taxonomy's own containment claim.

### 2.5 Other one-way implications a reader would need (omissions)

- H2_loc-inextendibility ⇒ C2-inextendibility (actively forbidden in the C2 file; §2.4).
- C^{1,1}-inextendibility ⇒ C2-inextendibility; C1-inextendibility ⇒ C2-inextendibility.
- C0-inextendibility ⇒ H2_loc-inextendibility (under the taxonomy's own containment claim).
- distributional-vacuum C0 inextendibility ⇒ C2-inextendibility.
- bare C0 inextendibility ⇒ C^1/C^{1,1}/C^∞ inextendibility.
- two-sided inextendibility ⇒ future inextendibility (prose only in `#extension_predicate.why_future_not_two_sided`; acceptable, but not in the ledger).

### 2.6 Internal contradictions on the containment direction (R2-01, R2-02)

- C2 `#regularity.must_not_conflate[2]`: "a C0 result does not establish this class: it is stronger, and the implication runs C0 => C2 only (see implication_ledger)" — read literally this denies the entailment asserted by the same file's ledger and by `#class_boundary.one_way_implication` ("E(C0) entails E(C2) because every C2 extension is a C0 extension; the converse is forbidden"). The charitable reading is a labelling rule (a C0 result must be filed as the C0 class), but the frozen fields then disagree on their face.
- C0 `#non_vacuity.vacuity_falsifier`: "... (e.g. one already shown C2-inextendible by a stronger theorem), the citation adds no information and must be marked as subsumed, not as evidence for this class", and `#falsifier.schema_falsifiers[3]`: "the class is cited for a development already shown C2-inextendible and presented as new evidence: subsumed citation". These contradict the **repaired** `#non_vacuity.c0_specific_note` ("a C2-inextendibility proof does NOT subsume this class's conclusion. The implication runs C0 => C2 only: C0-inextendibility is the stronger statement, so a C2 result is weaker and citing it as if it established C0-inextendibility is conclusion inflation"), `#regularity.must_not_conflate[2]`, and `#implication_ledger.forbidden_transfers[0]`. A development shown C2-inextendible is not thereby C0-inextendible, so such a citation is unsupported, not "subsumed".

---

## 3. FUTURE vs TWO-SIDED (task item 3)

Clause (f), identical in both files:
> "(f) the extension adds points to the future: there exist q in iota(M) and p in M' minus iota(M) with p in I^+(q; g')."

### 3.1 Precision — NO (R2-05, major)

1. **I^+ is never defined**, and for the C0 class the curve convention changes the set: for continuous metrics the chronological future defined via locally Lipschitz curves may be non-open and may differ from the piecewise-C^1 version (Grant–Kunzinger–Sämann–Steinbauer, arXiv:1901.07996). The C0 file flags only geodesic uniqueness (`#extension_predicate.c0_uniqueness_caveat`).
2. **Chronological, not causal**: a future extension adding only J^+(q) \ I^+(q) points escapes the predicate, so "no proper future extension" is narrower than the natural causal reading; the choice is never justified.
3. **One q, not a Cauchy surface**: the class is not compared with standard future-extendibility formulations that use a Cauchy surface Σ (e.g. p ∈ I^+(Σ)).
4. **Boundary-only escape**: (b) only requires iota(M) open and proper; M' \ iota(M) may have empty interior (iota(M) dense open and proper), and if no added point is I^+-related to iota(M) the extension is invisible to the class. No nonempty-interior/achronality/density condition is stated.

### 3.2 Past/white-hole claim

`af_scc_c2_vacuum.yaml#extension_predicate.why_future_not_two_sided` (also `formulation_taxonomy.yaml#axis_registry.extension_direction.reason`):
> "one-ended AF data can be extendible to the PAST into a white-hole region without any failure of future determinism; two-sided inextendibility is a strictly stronger different statement"

- The **logical** claim survives: under (f), a past-only extension is not a proper future extension, so the directions are independent by definition of the frozen predicate; two-sided ⇒ future is correct.
- The **existence** claim is uncited (`#provenance.sources` identifiers all null), "white-hole region" is undefined, and it is not cross-referenced to the Kerr obstruction (time reversal) that would supply the witness. Severity minor (R2-08), but it motivates a frozen axis.

---

## 4. VACUITY (task item 4)

### 4.1 C2: asserted, not derived (R2-07, major)

`af_scc_c2_vacuum.yaml#non_vacuity.condition`:
> "for a future-complete development, a future extension is impossible already for elementary reasons (a maximal geodesic of the complete development cannot terminate at a boundary point of the extension), so the conclusion would be vacuous"

`#non_vacuity.c2_specific_note`: "in the C2 class the vacuity argument is elementary because geodesics of a C2 metric are unique".

Spelled-out requirement: (1) M future timelike geodesically complete; (2) suppose a proper future extension and p ∈ I^+(q;g') \ iota(M); (3) for C2, I^+(q;g') is open in M'; (4) the timelike curve exits iota(M) at x ∈ ∂iota(M); (5) produce a **maximal** (distance-realizing) timelike geodesic of M terminating at ∂iota(M) in finite affine parameter, or an equivalent contradiction via a Cauchy surface of M and the Lorentzian distance. Step (5) is exactly what the parenthetical assumes; it does not follow from geodesic uniqueness, M' is not assumed globally hyperbolic, and the added point need not be at finite Lorentzian distance from iota(M). Geodesic completeness does not universally block extendibility in Lorentzian geometry (de Sitter Poincaré-patch phenomenon; in vacuum, Taub-NUT and the Kerr/RN Cauchy horizons are the standard extendible-MGDH examples — Rendall, arXiv:gr-qc/0503112: "It may happen that the maximal Cauchy development can be extended to a larger spacetime ... its boundary ... is called the Cauchy horizon ... A famous example where this happens is the Taub-NUT spacetime"). I could **not** construct or find a counterexample in the frozen AF Λ = 0 class, so I do not claim the statement is false; I claim it is unproved here, presented as "elementary", and `#non_vacuity.status` flags only membership of the witness family in G. `#non_vacuity.vacuity_falsifier` inherits the unproved premise.

### 4.2 C0: correctly flagged as NOT automatic — NO FINDING

`af_scc_c0_vacuum.yaml#extension_predicate.c0_uniqueness_caveat` and `#non_vacuity.condition` correctly state that for merely continuous metrics the classical geodesic equation is undefined, local geodesic uniqueness is not automatic, and the completeness argument cannot be imported. Residual: the positive non-vacuity argument on the witness family is left as an expectation and membership in G is UNVERIFIED (acknowledged in the file). Attempted counterexample: none found; note that with I^+ ambiguous for C0 metrics (§3.1) the C0 vacuity claim is convention-dependent as well.

---

## 5. CONCLUSION TYPE (task item 5)

- **WCC leakage (I+ completeness, asymptotic predictability, visibility): NO FINDING.** Both `#conclusion`, `#visibility`, `#i_plus` and `#falsifier` are SCC-shaped; `#visibility.role: not_in_conclusion` with a reason; `#i_plus.role: assumption`, `#i_plus.in_conclusion: false`; `#conclusion.forbidden_strengthenings` explicitly bans WCC content; the SCC tier_1 witness is an extension, not a visible geodesic. Gate R09/R10/R12 pass.
- **Deriving the other regularity class's conclusion:** the licensed direction C0 ⇒ C2 is stated in both ledgers, in C2 `#class_boundary.one_way_implication` and in C0 `#c0_specifics.conclusion_relation_to_sibling`, and is correct (R2-04 caveat). The reverse is correctly forbidden in both files. I found **no unlicensed derivation**. The only defect here is the wording contradiction R2-01, which is a false statement in a frozen block but creates no leak.
- New status material is properly quarantined: C0 `#c0_specifics.candidate_tool` (arXiv:1507.00601) and `#provenance.known_status_signals` (Dafermos–Luk arXiv:1710.01722, "the literal AF-SCC-C0-VAC-GEN class is expected FALSE conditional on Kerr exterior stability") are both `citation_status: unresolved` and explicitly "NOT asserted by this schema". **NO FINDING**; good status hygiene.

---

## 6. KNOWN OBSTRUCTION (task item 6)

`af_scc_c2_vacuum.yaml#conclusion.known_obstruction` (and C0 counterpart):
> "the exact stationary (Kerr) vacuum data admit a C-infinity vacuum extension, so the unqualified statement over ALL AF vacuum data is false; the class is only meaningful with the generic quantifier ... citation_status: unresolved (L1 owns the anchor)."

- Status: **UNVERIFIED in this session at the artifact's own standard.** I confirmed at survey level that Kerr (and Reissner–Nordström) replace the Schwarzschild singularity by a Cauchy horizon, i.e. that the maximal development is extendible across it (Rendall, arXiv:gr-qc/0503112 §3), and that Taub-NUT is a standard extendible maximal Cauchy development; I did not verify the specific "exact Kerr AF initial data have a MGHD with a proper future C^∞ vacuum extension" statement from a primary source. Both files mark it unresolved (`#genericity.excluded_set_status`, `#provenance.sources`).
- Structural dependence: none as evidence. It appears only to motivate genericity, to justify the conditional wording of `#conclusion.forbidden_strengthenings` ("false if the Kerr obstruction is as stated"), and as the "e.g." witness in `#falsifier.tier_2` (labelled `refutes_strengthening_only`). The frozen conclusion and predicates are unchanged if the claim is false. **No structural finding.**

---

## 7. BOUNDARY CASES (task item 7)

**E1 — H2_loc extension: M' smooth, g' continuous nondegenerate Lorentzian, second derivatives/curvature locally L^2, no equation, g' not C^1.**
- C2 schema: **NOT in class.** Clause (d) fails; `#regularity.extension_regularity_exact` says "NOT H2_loc"; `#regularity.must_not_conflate[1]` separates the curvature axis from metric differentiability. No ambiguity.
- C0 schema: **AMBIGUOUS at the object level (R2-06, minor).** Clause (d) ("continuous, nondegenerate Lorentzian metric") + (e) ("NO equation is required") admit E1: it IS a proper future C0 metric extension and a valid C0 tier_1 falsifier. But `#extension_predicate.must_not_conflate[0]` says "extensions with locally square-integrable curvature (H2_loc) are a DIFFERENT class; H2_loc is not C0". Rev4/5's `#regularity.must_not_conflate[0]` now says "No containment with C2 or C0 is asserted here", which removes the false containment claim but leaves the object-level question open. Guidance for *theorems* is right (an H2_loc-inextendibility result must not be filed as C0); guidance for *witnesses* is unclear.

**E2 — extension metric C2, Ric = 0 only distributionally (no classical pointwise check).**
- C2 schema: **IN class**, but the schema never says so. For a C2 metric Ric is continuous, and a continuous tensor vanishing distributionally vanishes pointwise, so clause (e) is automatically satisfied. A literal reader may misclassify (R2-14, nit).
- C0 schema: **IN class** (bare; clause (e) requires no equation), and also in the undefined distributional variant (R2-09).

**E3 — C^{1,1} but not C2 metric, no equation.**
- C2 schema: NOT in class; the "NOT C^{1,1}" phrase is class identity, not set disjointness (every C2 metric is C^{1,1}). C0 schema: IN class (C^{1,1} ⇒ C0). Consequence recorded in no ledger: C^{1,1}-inextendibility ⇒ C2-inextendibility (R2-12, §2.5).

---

## 8. Findings register (against rev5)

| id | severity | one-line | exact paths |
|---|---|---|---|
| R2-01 | major | C2 `must_not_conflate` denies the C0 ⇒ C2 entailment asserted by the same file's ledger and `class_boundary` | `af_scc_c2_vacuum.yaml#regularity.must_not_conflate[2]` vs `#implication_ledger.one_way_entailments[0]`, `#class_boundary.one_way_implication` |
| R2-02 | major | C0 `vacuity_falsifier` and `schema_falsifiers[3]` still assert the inverted "subsumed citation" example that rev4 repaired in `c0_specific_note` | `af_scc_c0_vacuum.yaml#non_vacuity.vacuity_falsifier`, `#falsifier.schema_falsifiers[3]` vs `#non_vacuity.c0_specific_note`, `#regularity.must_not_conflate[2]`, `#implication_ledger.forbidden_transfers[0]` |
| R2-03 | major | False `forbidden_transfer` H2_loc → C2 (C2 metrics are locally H2_loc); "no containment with C2 is asserted" cannot coexist with it; taxonomy still wrong | `af_scc_c2_vacuum.yaml#implication_ledger.forbidden_transfers[1]`, `#regularity.must_not_conflate[1]`; `formulation_taxonomy.yaml#implication_ledger[5]`, `#axis_registry.regularity_axis.containment`, `#class_contracts.AF-SCC-C0-VAC-GEN.negative_test_case.reason` |
| R2-04 | major | C0 rev4/5 pinned M' smooth in clause (c) but did not propagate: `extension_topology` still says "NOT assumed smooth", `topology.forbidden[2]` still reads "assuming M' is a smooth manifold with a C2 metric", tier_1 witness still says "topological manifold"; iota's regularity still unfrozen in both files | `af_scc_c0_vacuum.yaml#extension_predicate.definition` (a),(c); `#topology.extension_topology`; `#topology.forbidden[2]`; `#falsifier.tier_1.witness_type` |
| R2-05 | major | Clause (f) under-specified: I^+ undefined/convention-dependent for C0, chronological vs causal, single q, boundary-only extensions escape | both files `#extension_predicate.definition` (f); `af_scc_c0_vacuum.yaml#extension_predicate.c0_uniqueness_caveat` |
| R2-06 | minor | H2_loc extension is admitted by the C0 predicate but the prose says "H2_loc is not C0" (object vs statement-class conflation) | `af_scc_c0_vacuum.yaml#extension_predicate.must_not_conflate[0]` vs `#extension_predicate.definition` (d),(e), `#regularity.must_not_conflate[0]` |
| R2-07 | major | C2 vacuity argument asserted as "elementary"; the stated reason is a non sequitur; unproved and unflagged | `af_scc_c2_vacuum.yaml#non_vacuity.condition`, `#non_vacuity.c2_specific_note`, `#non_vacuity.status` |
| R2-08 | minor | Uncited existence claim "one-ended AF data can be extendible to the PAST into a white-hole region"; no cross-reference to Kerr/time reversal | `af_scc_c2_vacuum.yaml#extension_predicate.why_future_not_two_sided`; `formulation_taxonomy.yaml#axis_registry.extension_direction.reason` |
| R2-09 | minor | Distributional-vacuum C0 variant undefined (no frozen predicate), so claim (iii) is only conditional; "see variants" points to genericity variants that do not contain it | `af_scc_c0_vacuum.yaml#regularity.must_not_conflate[1]`, `#implication_ledger.one_way_entailments[1]`, `#anti_scope.not_this_class[4]`, `#genericity.variants` |
| R2-10 | minor | "replacing future by two-sided direction" listed under `forbidden_weakenings`, but two-sided is strictly stronger | `af_scc_c2_vacuum.yaml#conclusion.forbidden_weakenings[2]`; `af_scc_c0_vacuum.yaml#conclusion.forbidden_weakenings[3]` |
| R2-11 | minor | C0 `forbidden_strengthenings[0]` lists C2/C1/H2_loc, which its own parenthetical says are NOT stronger than C0 | `af_scc_c0_vacuum.yaml#conclusion.forbidden_strengthenings[0]` |
| R2-12 | minor | "NOT C^{1,1}, NOT C1, ..., NOT H2_loc" reads as set disjointness although C2 ⊂ C1, C^{1,1}, H2_loc; "NOT smooth-only" ambiguous | `af_scc_c2_vacuum.yaml#regularity.extension_regularity_exact` |
| R2-13 | nit | Unbound parameter k ("k >= 3; k is part of the assumption") absent from D0 and the formal quantifier; "machine checkable" steps rely on sampling a pointwise identity/regularity | both files `#regularity.i_plus_regularity`; `#falsifier.tier_1.machine_checkable_steps` |
| R2-14 | nit | At C2 regularity classical and distributional Ric = 0 coincide; the equation and regularity axes are not independent, but the taxonomy presents them as independently frozen | `formulation_taxonomy.yaml#axis_registry.extension_equation_requirement`; both files `#extension_predicate.definition` (e) |
| R2-16 | minor | `dense_escape` variant is not in `genericity_kind` (rule_spec defines it but omits it from the vocabulary list) and its `statement_strength: incomparable` contradicts rule_spec's "residual_comeager => dense_escape" and the taxonomy containment note (dense form is strictly weaker) | both files `#genericity.variants[dense_escape]`; `rule_spec.json#vocabularies.genericity_kind`, `#vocabularies.genericity_kind_definitions.dense_escape`, `#vocabularies.genericity_implications`; `formulation_taxonomy.yaml#axis_registry.genericity_axis` |
| R2-17 | minor | Positive transfers (`direction: transfers`, two entries in rev5) now sit inside the block named `transfer_failures`; category error and gate-blind (R07 only checks non-emptiness) | `af_scc_c2_vacuum.yaml#genericity.transfer_failures`; `af_scc_c0_vacuum.yaml#genericity.transfer_failures` |

## 9. No-finding categories (explicit)

1. **Literal separation of the frozen regularity/equation slots** (item 1): NO FINDING. See §1.2.
2. **WCC content in conclusion/visibility/i_plus/falsifier**: NO FINDING. No I+ completeness, asymptotic predictability or visibility is derivable; both files forbid it; gate R09/R10/R12 pass.
3. **Unlicensed cross-class derivation**: NO FINDING. C2 ⇒ C0 is forbidden in both files; WCC ↔ SCC is forbidden; the licensed C0 ⇒ C2 direction is correct.
4. **C0 flagging that the completeness argument does not transfer**: NO FINDING (§4.2).
5. **Quantifier structure**: NO FINDING. `ordered`/`formal`/`negation`/`negation_normal_form` are mutually consistent, and "non-meager ⟺ meets every comeager set" is valid. (The rev5 tier_1 logic now matches it; see §10.)
6. **Class identity blocks**: NO FINDING. `class_id`, `node_id`, `class_components`, `sibling_disjoint_from`, `anti_scope`, `conclusion_type` are distinct and consistent between the files and the taxonomy contracts.
7. **Kerr obstruction used as evidence**: NO FINDING on structure (§6); flagged UNVERIFIED as a factual claim. The C0 status signals are properly quarantined (§5).
8. **rev5 genericity well-definedness**: NO FINDING on the new `ambient_space`/`topology_or_measure` text (constraint-manifold subspace topology, Baire-ness, quotient no longer used for comeagreness) — this is a genuine improvement.

## 10. Repairs verified during the review

- **rev4**: C0 `#regularity.must_not_conflate[0]` "H2_loc ... is strictly between C2 and C0" → "a distinct regularity-axis value phrased in terms of CURVATURE ... No containment with C2 or C0 is asserted here". Partially repaired (taxonomy still says "strictly between").
- **rev4**: C0 `#non_vacuity.c0_specific_note` "a C2-inextendibility proof SUBSUMES this class's conclusion" → "does NOT subsume ... conclusion inflation". Repaired (R2-02 residue remains in two sibling fields).
- **rev4**: C0 `#extension_predicate.definition` (c) "M' is a topological 4-manifold" → "M' is a SMOOTH (C-infinity) connected 4-manifold ... the metric itself is only continuous". Repaired in the predicate (residues: R2-04).
- **rev4**: genericity dense-open strength corrected to `strictly_stronger` with the right implication direction.
- **rev5**: tier_1 falsifier logic corrected: "tier 1 refutes the class by showing the EXTENDIBLE set is non-meager ... One extendible datum is NOT sufficient in general because G is existentially quantified and individual membership is undecided. Route R1 = non-meagerness (general); route R2 = a datum in an explicitly instantiated generic set G* (instantiated claims only)." This is the repair of the invalid route I identified in rev4 (and R1 identified independently); it now matches `#quantifiers.negation_normal_form` and `rule_spec.json#vocabularies.membership_ruling`. **No finding.**
- **rev5**: genericity well-definedness (constraint-manifold subspace topology; Baire-ness; quotient not used for comeagreness) and additional transfer witnesses. **No finding** except the block-name issue R2-17.
- The gate passes on rev5; the gate cannot see any of the remaining findings (no semantic checks; variants not checked by R07; R16 cannot detect a false forbidden transfer).

## 11. Sources consulted (external, untrusted data)

- J. D. E. Grant, M. Kunzinger, C. Sämann, R. Steinbauer, "The future is not always open", Lett. Math. Phys. 109 (2019) — arXiv:1901.07996 — chronological futures for continuous metrics may be non-open and curve-class dependent. https://ar5iv.labs.arxiv.org/html/1901.07996
- A. D. Rendall, "The nature of spacetime singularities", arXiv:gr-qc/0503112 — extendible maximal Cauchy developments and Cauchy horizons (Taub-NUT; Kerr/RN); the ambiguity of SCC under the regularity/equation choice of extension. https://arxiv.org/html/gr-qc/0503112v1
- Standard Sobolev borderline fact used in §2.4: H^2_loc(R^4) ⊄ C^0 (k = n/p = 2).
