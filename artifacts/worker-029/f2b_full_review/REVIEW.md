# W029-F2B-FULLVERDICT-01 — independent full-schema review of F2b (AF-SCC-C0-VAC-GEN)

- reviewer: worker-029 | verdict: **revise** | score: 2.0/5 | created_at: 2026-09-12T00:23:49+08:00
- artifact: `schemas/af_scc_c0_vacuum.yaml` @ `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` (snapshot copy `f2b_snapshot.yaml`)
- live path identical at emission: **True** (`1bb78ce9b357`)
- machine summary: {'PASS': 21, 'FAIL': 5, 'WARN': 2} | hard-failure checks: ['C5', 'F1', 'F2', 'G1', 'G2']

## Hard failures (block acceptance at this hash)

### HF-29-01 (C5)

class_contract_pointer = 'artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN' targets the authoring tree. The canonical-path policy in force since 2026-09-12 (ASTRA_HANDOFF) makes research_map/formulation_taxonomy.yaml authoritative, and that file has no 'class_contracts' key (its class definitions live under 'classes'). The pointer does resolve at the authoring path, but the class contract this schema binds to is not resolvable at the authoritative path, so G-FORM's class binding cannot be checked against the canonical artifact.

falsifier: Show class_contracts.AF-SCC-C0-VAC-GEN in the canonical research_map/formulation_taxonomy.yaml, or a controller record reversing the canonical-path policy.

### HF-29-02 (F1,F2)

l1_ledger_refs marks D-002, T-301, T-302, T-515, T-528 as 'citation_status: verified_by_L1' while the cited rows in ledger/theorems.jsonl @ce42d205 record verification_status='abstract-read' for all 62 rows (61 abstract-read, 1 unverified, 0 verified). The token 'verified_by_L1' occurs in neither ledger/theorems.jsonl nor ledger/citation_audit.csv (whose verdict vocabulary is 'verified' on abstract/API evidence). The same artifact sets provenance.citation_status='unverified', so it contradicts itself and overstates the ledger's verification level. G-LIT's criterion requires verification_status to be honest.

falsifier: Produce one of: a ledger/theorems.jsonl row for those ids with verification_status='verified'; a project definition equating 'verified_by_L1' with citation_audit.csv verdict='verified' on abstract evidence; or a corrected revision whose l1_ledger_refs token is traceable.

### HF-29-03 (G1,G2)

revised_at = '2026-09-12T00:30:00+08:00' and f0_binding.checked_at = the same value are future-dated by +370 s at the snapshot instant (2026-09-12T00:23:49+08:00), and checked_at postdates the taxonomy_consistency.json evidence file (mtime 2026-09-12T00:23:05+08:00) by a fictional interval. The artifact's own f0_binding rule makes a gate verdict conditional on that consistency re-run. This is controller finding CF-14 (future-dated records make 'binding at measured_at' unreliable) recurring inside the artifact.

falsifier: Show a wall-clock record proving the revision was written at or before 00:30 and that the snapshot clock was wrong; or reissue the revision with wall-clock revised_at/checked_at.

## Soft findings

### W-29-01 (D3, major)

quantifiers.formal binds a pair '(s,delta) in D0', but D0 is defined as the union of the Sobolev pairs and 'the smooth-with-decay default', which has no (s,delta) coordinates. The binder is ill-typed on that member and the statement reads as a family of statements (the same risk recorded for F2a as probe S6-C2). F2b-review-18 passed this field as 'no disjunctive binder remains'; this checker agrees the binder chain is a single chain but flags the domain typing. The identical D0 wording is present in F1 and F2a, so this is a cross-artifact convention, not an F2b-only defect.

falsifier: Exhibit an explicit index set in which the smooth default is a named element carrying (s,delta) coordinates, or state D0 as a pair-indexed part plus a constant part.

### W-29-02 (C3, info)

Two raw 'C0 or C2'-pattern occurrences remain: line 157 ('No containment with C2 or C0 is asserted here') and line 283 (quoted in anti_scope.phrases_that_are_not_this_class). Both are negated/quoted prohibitions; the line-5 YAML comment that F2b-review-18 HF-B1 rejected is gone. Process note: the map's F2b next_falsifier literally says any reintroduction of a composite 'C0 or C2' string rejects the revision, while the class-separation gate exempts prohibition keys; reconcile the two readings.

falsifier: A revision containing an assertion-like (non-negated, non-quoted) composite regularity token, or a recorded decision to relax the literal next_falsifier.

### W-29-03 (E1b, minor)

Vocabulary check: F2b's conclusion token 'scc_c0_future_inextendibility' is alias-equivalent to the canonical F0 token 'strong_cosmic_censorship_C0' under artifacts/formulation/VOCAB_ALIASES.json, so this is NOT a defect of F2b. Observed for the controller/F0 owner: the canonical taxonomy carries the registered alias, and the alias policy says accepted aliases 'must never appear in a new canonical artifact'; G-FORM's wording 'exact conclusion_type' should record whether alias-equivalence satisfies it.

falsifier: A recorded controller decision that alias-equivalence satisfies G-FORM, or an F0 revision adopting the registry key token.

## Positives (checks that passed)

- A1: snapshot parses as YAML mapping
- A2: class_id exact
- A3: node_id == map node F2b
- A4: sibling_disjoint_from names the C2 class
- A5: C2 sibling declares the C0 class symmetrically
- B1: G-FORM contract fields present
- C1: class_components decode the class id (AF/SCC/VAC/GEN/C0)
- C1b: class_components match canonical F0 axes through the vocabulary map
- C3: no assertion-like merged-class pattern (prohibition mentions allowed)
- C5b: declared pointer resolves at the path it names
- C6: F0 declared binding hash equals the canonical taxonomy hash at snapshot
- D1: binder order forall-exists(comeager)-forall-not_exists
- D2: comeager quantifier bound to the data-independent set
- D4: negation and negation normal form present
- D5: conclusion.statement_formal preserves the quantifier order of quantifiers.formal
- E1: schema conclusion_type is alias-equivalent to the canonical F0 class token
- E2: C0=>C2 one-way direction asserted; C2=>C0 forbidden
- E3: I+ / visibility excluded from the conclusion
- E4: no theorem promotion: epistemic_status=open_problem + promotion rule
- F3: class_identity_variants/anti_scope variant ids exist in VARIANT_REGISTRY
- G3: revision is an integer >= 1 and authored_at precedes revised_at
- HF-B1 regression from F2b-review-18 is fixed: the line-5 'C0 or C2' comment is gone (checked in raw text).
- HF-B2 (node identity) is fixed: node_id=F2b matches the map's F2b node and the F2a/F2b split.
- f0_binding.declared_f0_sha256 equals the measured canonical taxonomy hash 276009f4f63d at snapshot.
- Variant registry entries CH / H2LOC / DISTRIBUTIONAL referenced by the schema exist in VARIANT_REGISTRY.json.
- F2a declares the C0 sibling symmetrically (sibling_disjoint_from), and the C0=>C2 one-way direction is asserted.

## Reproduce

```bash
cd artifacts/worker-029/f2b_full_review
python3 check_f2b_full.py --dir . --live-root ../../.. --out report.json
python3 emit_w029.py
```

## Scope and authority

This is an independent worker review. It does not set a gate verdict, a node status, or a
validation_status; it is evidence for A1/G-FORM at the pinned sha256 only.
