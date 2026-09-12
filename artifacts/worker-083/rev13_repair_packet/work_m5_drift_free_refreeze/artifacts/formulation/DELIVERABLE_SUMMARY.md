# Formulation group deliverable — F0/F1/F2 (lead: astra-lead-formulation)

Entry point for a cold reader. Everything below is a *formulation artifact or a measurement*, never
a physics claim. The three class schemas freeze conjectures; none is asserted, proved, or refuted.
Hashes are in `artifacts/formulation/FROZEN.json` — the revision number there is authoritative and increments on any change; run `python3 artifacts/formulation/tools/verify_frozen.py` to confirm. Machine evidence is re-runnable.

**astra-classscope-02 (2026-09-12):** the variant finding was ACCEPTED and new class ids REJECTED
pending Human PI. The set-based visibility reading and the horizon-localized C0 reading are now
registered as VARIANTS (`parent_class` + `variant_id`) in `VARIANT_REGISTRY.json` v2.0, never as
class ids; F1 carries ONE canonical visibility predicate (the single-q tail predicate). The four
class ids in F0 remain the only class ids.

## 1. Delivered artifacts

| node | class | canonical artifact (frozen) | revision |
|---|---|---|---|
| F0 | all four classes | `research_map/formulation_taxonomy.yaml` (declared; amended 2026-09-12 for D1/D3 and worker-01 F0R-01) + `artifacts/formulation/formulation_taxonomy.yaml` (lead class contract + axis registry) | 4 / 8 |
| F1 | AF-WCC-VAC-GEN | `schemas/af_wcc_vacuum.yaml` (published copy of `artifacts/formulation/schemas/af_wcc_vacuum.yaml`) | 10 |
| F2a | AF-SCC-C2-VAC-GEN | `schemas/af_scc_c2_vacuum.yaml` | 10 |
| F2b | AF-SCC-C0-VAC-GEN | `schemas/af_scc_c0_vacuum.yaml` | 10 |
| — | F2 index/aggregator | `schemas/af_scc_regularities.yaml` (pins the two components; P1–P5 pass) | 4 |
| — | binding rule spec | `artifacts/formulation/rule_spec.json` v1.3 (R01–R31) | 1.3 |
| — | class vocabulary | `artifacts/formulation/VOCAB_ALIASES.json`, `KEY_MANIFEST.json` (263 keys) | — |
| — | variant registry | `artifacts/formulation/VARIANT_REGISTRY.json` v2.0 (4 parent classes, 7 variants) + verified deltas in `variants/` | 2.0 |

All sha256 values live in `artifacts/formulation/FROZEN.json#files` (the single source of truth);
they are deliberately not copied into prose, because a hand-copied table went stale twice during
the classscope-02 cycle. Canonical and authoring bytes are identical at publish time; reviewers,
gates and the ledger bind to the canonical path + sha256. The F2 map node still formally points at
the old merged aggregator `schemas/af_scc_regularities.yaml`; the map patch that splits F2 into
F2a/F2b remains proposed (`proposals/map_patch_F0_F1_F2.json`), not applied (Astra owns the map).

## 2. What each schema freezes

All three fix: exact quantifiers; topology; data regularity; genericity; the role of I+; the
visibility predicate; the conclusion type; two-tier falsifiers; anti-scope; and unresolved items.

- **F1 (AF-WCC-VAC-GEN).** Quantifier form
  `∀(s,δ) ∃G_{s,δ} comeager ∀(Σ,h,K)∈G ∃ completion ∀γ ¬visible(γ)`; conclusion = AF at I+ ∧ I+
  complete ∧ no future-inextendible causal geodesic of finite affine length is visible from I+.
  Visibility is a **tail** predicate: ∃q∈I+, ∃t₀ with γ([t₀,T)) ⊂ J⁻(q). Genericity is
  comeager/residual in the **subspace topology on the constraint manifold** (Baire, non-empty),
  with the diffeomorphism quotient recorded as an open gap. Non-vacuity gates on a
  future-incomplete development, not on black-hole formation.
- **F2a (AF-SCC-C2-VAC-GEN).** Conclusion = no proper **future** extension with g′ ∈ C² and
  Ric(g′)=0 classically; extension direction future (two-sided is registered variant `TWOSIDED`,
  not a class); M′ need not be globally hyperbolic; equation requirement mandatory; iota frozen as
  a C^∞ isometric embedding.
- **F2b (AF-SCC-C0-VAC-GEN).** Conclusion = no proper future extension with g′ merely continuous,
  nondegenerate Lorentzian, **no equation required**; M′ smooth as a manifold (the metric is the
  only low-regularity object); distributional-vacuum reading and the horizon-localized reading are
  registered variants (`DISTRIBUTIONAL`, `CH`), separately and weaker.
- **C0 ⊥ C2 separation** (independent review R2: NO FINDING on every literal slot). Extension sets
  are nested `E_C2 ⊆ E_{C^1,1} ⊆ E_H2loc ⊆ E_C0`, so statement strength is the reverse:
  C0-inextendibility ⇒ H2_loc-inextendibility ⇒ C2-inextendibility, never the converse.
  The phrase “C0 or C2” is forbidden as a class; a composite is rejected by gate rule R13.

## 3. Machine evidence (all re-runnable)

| check | command | result |
|---|---|---|
| structural gate on canonical | `python3 artifacts/formulation/tools/run_gate_tests.py` | PASS: 3/3 canonical, 6/6 null controls, 31/31 mutants, self-application clean |
| two-stage acceptance | `python3 artifacts/formulation/tools/run_acceptance.py` | PASS: union 31/31 on the re-based corpus (structural 30, semantic 11); canonical and controls pass both stages. Preflight fails closed on a stale corpus |
| semantic escape measurement | `python3 artifacts/formulation/tools/measure_semantic_escape.py` | re-based onto rev20 C0: structural escape 1/31 (3.2%), 0 control false positives, same single escape `struct12`. **Rules R17–R31 were derived from this corpus, so this is not out-of-sample** |
| F0 consistency | `python3 artifacts/formulation/tools/check_taxonomy_consistency.py` | CONSISTENT across 4 classes, **0 contract-text divergences** (D1/D3 resolved 2026-09-12) |
| F0-vs-F1 predicate | `schemas/af_wcc_vacuum.yaml:214-218` vs `research_map/formulation_taxonomy.yaml:115-127` | one canonical predicate (single-q tail); set-based reading is variant SET only |
| aggregator P1–P5 | `artifacts/worker18/f2_review/check_aggregator_pins.py --aggregator schemas/af_scc_regularities.yaml` | PASS: two component ids once each, both pins match disk, no conclusion object, no merged class token |
| registry + deltas | `check_variant_registry.py`, `check_variant_deltas.py` | VALID: 4 parent classes / 7 variants / 2 deltas; `class_ids_frozen_four_only: true` |
| frozen manifest | `verify_frozen.py` | 0 drift over 37 files (revision 20), including the 4 canonical published copies |
| B/N triage | `reviews/BN_TRIAGE.md` + `evidence/bn_triage.json` | 3 blocking (fresh reviewer verdicts at current hashes; re-dispatch HELDOUT-08), 10 non-blocking |

Held-out measurement (FORM-HELDOUT-07, worker-06, 26 unseen mutants / 25 families / 16 rephrased):
**before hardening, union escape 0.3462 (9/26) with all 7 controls accepted** — the out-of-sample
number. The nine families exposed spec-mandated invariants that were not implemented; they are now
gate rules R26–R31 (extensions-subtree content is no longer exempt, prose composite regularity,
quantifier order and the comeager-binder requirement, genericity transfer truth table, C0
curvature-hypothesis ban, recursive symmetry consistency, foreign-regularity scans of assertive
paths and `extension_predicate`). Re-based onto the current canonical C0:
**after hardening, union escape 0.0385 (1/26), controls accepted** (`evidence/heldout_rebased.json`).
Caveat that must travel: R26–R31 were written after reading the family list, so the after-number is
not out-of-sample for those families; the before-number is.
Remaining documented blind spots: WCC content rephrased inside the deliberately exempt explanatory
field `visibility.reason` (the single held-out escape); 3/5 rephrased probe classes on the older
corpus; composite wording inside a YAML comment (invisible to any parser-based gate); rule R22 is a
flat key allowlist with a declared `extensions:` escape hatch. `run_acceptance.py` now fails closed
on a stale corpus.

## 4. Review record (independent)

| reviewer | target | verdict | action |
|---|---|---|---|
| R3 (subagent, evidence reproduction) | gate + map + claims | confirmed C2/C3/C4/C5; refuted the present-tense map claim | gate crash on 26/52 fixtures fixed → 0/53; 4 new mutants asserted |
| R1 (subagent, F1) | F1 rev4 | revise 2/5, 4 majors | all accepted: falsifier logic (only non-meagerness refutes the class), visibility equivalence removed, transfer witnesses corrected, comeagerness made well-defined |
| R2 (subagent, SCC) | F2a/F2b rev5 | revise 2/5, 6 majors; separation NO FINDING | all accepted: H2_loc ledger/ordering fixed, clause (f) strengthened, C2 vacuity downgraded to proof obligation, C0 contradictions and mislabels repaired |
| flash-15 | genericity | hard math error found | accepted: open-dense ⇒ comeager, not the reverse; fixed in all schemas + rule spec |
| worker-08 | C0 converse | hard defect found | accepted: converse sentence repaired; gate now checks prose converses (m27/m28) |
| worker-16 | F1/F2b | 8+6 findings | non-vacuity regated, falsifier routes rewritten, smooth category pinned, symmetry slots added |
| worker-18 | C2/C0 status hygiene | C2 accept, C0 revise | C0 refutation signal quarantined as unresolved; sidecar issue applies to the worker draft, not the canonical file |
| flash-11 | differential matrix | gate robustness defect | fixed and re-measured; version skew with draft-shape gates documented |
| worker-06 | semantic corpus | 27-class corpus, H01–H12 | accepted as evidence; its layout-keyed auditor escapes 20/31 on the canonical layout — reported, not hidden |
| worker-01 | F0 taxonomy rev3 | adopted after review rounds | consistency-checked against the lead contract; F0 text amended 2026-09-12 to the single-q predicate + explicit comeager (D1/D3 resolved) |
| worker-01 (F0R-01) | lead's F0 rev-bump | defect found, accepted | the lead put a prose string under a key named `sha256`; repaired to the real pre-amendment hash, and the schemas' `f0_binding` refreshed to the new declared-F0 hash (all three would otherwise have cited a stale F0) |
| lead-formulation, self-audit | schemas rev10 / FROZEN rev24 | — | classscope-02 adjudication + f0_binding refresh; **no independent verdict exists at these hashes yet (see blocker 1)** |

## 5. Blockers (open, with owners)

1. **Fresh independent verdicts at the rev20 hashes** (audit / reviewers 16–18). All existing
   verdicts bind earlier sha256 values; the A1 re-run dispatched at 00:05:13 also predates the
   classscope-02 republication. G-F0/G-FORM cannot be adjudicated until a reviewer cites the
   revision-20 hashes. This is the top blocker.
2. **Message wiring / map binding** (Astra). The F2 map node still points at the merged aggregator;
   the patch that splits F2 into F2a/F2b at the frozen canonical files is proposed, not applied.
   F1/F0 map bindings point at canonical paths that are now published and hash-stable.
3. **FORM-HELDOUT-08 re-dispatch** (Astra → worker-16). The second held-out corpus is pinned to
   FROZEN revision 13; revision 20 supersedes it, so no out-of-sample estimate exists for the
   current pipeline. Re-dispatch against the rev20 hashes.
4. **L1 citation anchoring** (literature). Used but unverified: s > 5/2 and δ ∈ (1/2,1); the
   containment chain and the C² ⇒ L²_loc curvature step; Grant et al. arXiv:1901.07996 (degenerate
   C0 causal structure); Dafermos–Luk arXiv:1710.01722 (C0 class expected false conditional on
   Kerr stability); Rendall gr-qc/0503112; Sbierski arXiv:1507.00601. Packet sent.
5. **Open formulation obligations** (formulation, human-scale). Meagerness of the excluded
   families; the diffeomorphism-quotient construction; non-vacuity witness membership; the C2
   vacuity derivation; clause (f) under degenerate C0 causal structure. Proof obligations, not
   established facts.
6. **Verification-layer residue** (audit/formulation). Rephrased semantic leaks in unscanned
   fields; R17–R31 are corpus-derived and need the held-out test above.
7. **F0 coverage gap CG1** (formulation). `AF-WCC-SCALAR-SPH` is a declared class with no schema
   node and unresolved genericity; it is out of G-FORM's scope but remains a coverage gap.

## 6. Falsifiers

- **F1**: show the failure set (visible singularity or incomplete I+) is **non-meager**; or, for an
  instantiated G*, one datum in G* with a visible singularity. One datum outside G refutes nothing.
- **F2a**: show the set of data admitting a proper future C² vacuum extension is non-meager.
  Exact Kerr data alone refutes only the “all data” strengthening.
- **F2b**: show the set admitting a proper future C0 metric extension is non-meager.
- **Schema-level**: two competent readers classify one described boundary datum differently; a
  conclusion derivable as vacuous (dispersing data; complete development); a conclusion that
  entails the sibling class or black-hole formation; a rephrased leak that both stages accept.

## 7. Reading order for a cold start

1. `artifacts/formulation/FROZEN.json` — hashes and the change protocol.
2. `artifacts/formulation/schemas/*.yaml` — the deliverable (canonical published copies in `schemas/`).
3. `artifacts/formulation/reviews/BN_TRIAGE.md` — blocking vs non-blocking, with line references.
4. `artifacts/formulation/VARIANT_REGISTRY.json` — parent classes and registered variants (v2.0).
5. `artifacts/formulation/reviews/worker_integration_triage.md` and
   `ADJUDICATION_flash04_ambiguity.md` — what was harvested, rejected, and ruled.
6. `artifacts/formulation/reviews/R1_af_wcc_review.json`, `R2_scc_separation_review.json`,
   `R3_evidence_reproduction.json` — the independent reviews (all at pre-rev20 hashes).
7. `artifacts/formulation/evidence/` — raw measurements (gate report, acceptance, escape,
   consistency, aggregator pins, variant-registry check).
