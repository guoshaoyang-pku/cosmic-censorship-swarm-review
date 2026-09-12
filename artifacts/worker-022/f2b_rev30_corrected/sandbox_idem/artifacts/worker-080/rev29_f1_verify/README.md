# W080-GFORM-R29-VIS-01 — independent F1 verification at FROZEN rev29

Bounded, class-bound, read-only worker task. Class `AF-WCC-VAC-GEN` (node F1, gate G-FORM).
Instance `worker-080-20260912T005226-968807`.

## Question

At the freshly frozen rev29 (schema revision 13, `schemas/af_wcc_vacuum.yaml`
`d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`), do the rev13 repairs hold
under an independently written checker, and does the declared F0/evidence binding chain
actually resolve?

rev13 claims, verbatim from the schema: (a) the D5/visibility definition now states the
whole-curve/tail **equivalence** for causal geodesics via past-closedness of `J^-(q)`; (b) the
variant `SET` relation is corrected from `strictly STRONGER` to `strictly WEAKER` as a
**predicate**; (c) `f0_binding.consistency_evidence_sha256` refreshed `675a99d0d25b` ->
`9e335e9ba1bf` in all three class schemas.

## Method

`verify_f1_rev29.py` (deterministic, offline) runs against the pinned copies in `pinned/` only
and writes `report.json` + `sandbox/check_taxonomy_consistency.out`. Thirteen checks:

| id | what it establishes |
|---|---|
| H1 | pinned schema/supplement/registry bytes equal the FROZEN rev29 declared sha256 |
| H2 | `f0_binding.declared_f0_sha256` equals the measured canonical F0 bytes (`0abb9ed8a961`) |
| H3 | all three schemas bind `consistency_evidence_sha256` to the measured evidence bytes (CF-20 #2) |
| H4 | class-contract pointer and supplement pointer resolve and name the declared class |
| H5 | case-corpus meta row binds the measured F0 rev5 hash; corpus is FROZEN-pinned (CF-20 #1) |
| H6 | `AF_{I+}` has one definition site and every use resolves (W080-FSYM-01 closure) |
| V1 | whole/tail equivalence for causal geodesics: finite exhaustive check over past-closed sets |
| V2 | single-q tail predicate entails the union predicate |
| V3 | union predicate does not entail single-q tail: omega-chain separation (T4) |
| C1 | single frozen class id; no composite C0/C2 token on any assertion surface |
| C2 | `conclusion_type` registered; tier-1 falsifier with machine-checkable witness steps |
| C3 | variant SET relation states the predicate-level direction correctly (rev13 repair) |
| X1 | canonical `check_taxonomy_consistency.py` re-run on the pins returns `CONSISTENT` |

The C1 scan is deliberately scoped to assertion surfaces: the schema *mentions* `C0 or C2` three
times inside `forbidden_weakenings` / `schema_falsifiers` / `anti_scope` prohibition lists, which
is the CF-16 metalinguistic-mention pattern, not a declaration.

## Result

**13/13 checks pass; 0 hard failures; verdict `accept` for the pinned bytes.**

- Hash chain: F1/F2a/F2b schemas, case corpus, canonical F0, supplement, VARIANT_REGISTRY all
  match the FROZEN rev29 declarations; the evidence-binding refresh to `9e335e9ba1bf` verifies in
  all three schemas. SUPERSEDED-hash reviews of the same schemas are evidence for their own pins
  only.
- Visibility: V1-V3 confirm the rev13 direction repair as a mathematical matter (the predicate
  `SET` is strictly weaker; the class statement using the union is strictly stronger).
- Symbol closure: `AF_{I+}` is defined once at `i_plus.predicate_abbreviation` and used only
  downstream; the W080-FSYM-01 undefined-symbol finding from rev11 is closed at rev29.

## Findings (recorded, not gate verdicts)

- **W080-F1-DIV-01 (major).** Level-conflated strength labels across frozen artifacts. F1 rev13
  correctly says variant `SET` is `strictly WEAKER than this class's single-q tail predicate`
  (predicate level), while the frozen canonical F0 class text (line ~200) and the frozen
  `VARIANT_REGISTRY.json` both say the set-based reading/condition is `strictly STRONGER`
  (statement level, because `P_tail => P_set`, so the SET class statement entails the base class
  statement). Neither states the level and no declared checker compares the fields. This is the
  same inversion class repaired at rev12->rev13 (W076-GFORM-STRICTNESS-RECONCILE-06,
  W040-F1-STRICTNESS-ADJ-04). Recommended: add explicit level labels to the variant entry
  (`relation: strictly_weaker` at predicate level, `statement_strength: strictly_stronger` at
  statement level — the schema already uses `statement_strength` for genericity variants) and
  record the F0/VARIANT_REGISTRY wording as a controller-adjudicated divergence (F0 bytes are
  frozen by REC-11; any F0 repair needs a fresh F0 review round).
  Licensed direction, machine-checked here: a `SET`-based proof establishes the
  `AF-WCC-VAC-GEN` conclusion a fortiori; a single-q (class) proof does **not** establish the
  `SET` variant statement.
- **W080-F1-MAN-01 (info).** `artifacts/formulation/FROZEN.json` bytes changed inside revision 29
  during this window (observed `3d9e3d77fd87...` at ~00:58 and `815e08079aef...` at 01:03;
  `frozen_at` 00:55:02 -> 00:57:26) while the three schema bytes stayed fixed. The manifest's own
  hash is not registered in `artifact_hashes.json`, so a manifest rewrite at constant revision is
  not caught by the declared-vs-measured drift check. Schema binding is unaffected.

## Verdict scope / authority

Worker evidence only. No gate verdict, no node status, no `validation_status=passed`, no
mathematical claim about WCC, no canonical artifact modified. The `accept` covers exactly the
thirteen checks at the pinned hashes above. Falsifier is carried in `report.json`.

## Files

- `verify_f1_rev29.py` — harness (exit 0 iff no hard failure)
- `report.json` — machine-readable result, findings, falsifier
- `sandbox/check_taxonomy_consistency.out` — canonical checker output on the pins
- `pinned/` — immutable input copies; `pinned_inputs.sha256`
- `SHA256SUMS` — hashes for event/evidence binding
