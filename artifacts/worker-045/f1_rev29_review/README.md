# W045-F1-REV29-GFORM-REVIEW-01 — independent F1 (AF-WCC-VAC-GEN) review at the FROZEN rev29 pin

Worker: `worker-045` (not an author of F1 or of any formulation artifact).
Node: **F1** · Class: **AF-WCC-VAC-GEN** · Gate: **G-FORM**.
Reviewed byte set: `schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`
(revision 13, canonical == authoring mirror), under `artifacts/formulation/FROZEN.json#815e08079aef`
(revision 29, frozen_at 2026-09-12T00:57:26+08:00).

## Result

**VERDICT `revise`, score 3.5/5 — 50 checks (48 PASS / 1 FAIL / 1 INFO), 9/9 falsification
controls, zero input drift in the read window.**

One blocking hard failure:

* **HF-045-1 — cross-artifact variant-SET direction contradiction.**
  F1 rev13 states variant SET is *"strictly WEAKER than this class's single-q tail predicate"*
  (the mathematically correct direction: the single-q tail predicate entails the union reading;
  the omega-chain witness separates them). `VARIANT_REGISTRY.json` `variants[SET].strength` and
  `variants/AF-WCC-VAC-GEN.variant-SET.delta.json` `strength` agree with F1.
  But F1's own declared binding target, the **G-F0-passed canonical**
  `research_map/formulation_taxonomy.yaml#0abb9ed8a961`, states the **opposite** in two live
  places: `classes.AF-WCC-VAC-GEN.conclusion.text` ("The set-based reading … is strictly
  stronger") and `variants[SET].definition` ("Strictly stronger than the parent class").
  A clean G-FORM accept would bind F1 as gate evidence while the class contract it declares
  asserts the opposite direction for a registered class-identity variant.

Per-source polarity census measured by check H9.5:

| source | direction |
|---|---|
| `F1.class_identity_variants[SET].relation` | weaker |
| `VARIANT_REGISTRY.variants[SET].strength` | weaker |
| `variant-SET.delta.strength` | weaker |
| `F0.classes[AF-WCC-VAC-GEN].conclusion.text` | **stronger** |
| `F0.variants[SET].definition` | **stronger** |

Routing note (not owned by this review): F1's own text is the correct side; the repair is
upstream. Any write to `research_map/formulation_taxonomy.yaml` voids G-F0 (REC-11) and requires
a fresh F0 round, so the alternatives are a controller ruling that the two F0 sentences are
documentation lag to be corrected at the next F0 revision, or a full F0 revision now.

## What passed

* **Pin fidelity** — every FROZEN rev29 pin for F1/F0/supplement/evidence/corpus/siblings matches
  the live bytes; canonical == authoring mirror; pre == post hashes (no drift).
* **Structure** — duplicate-key-rejecting YAML load; raw column-0 duplicate-key census; revision
  13; non-future `revised_at`; single frozen `class_id`.
* **Class identity / leakage** — one frozen class token; no C0/C2 composite; `conclusion_type`
  licensed for AF-WCC-VAC-GEN under `rule_spec.vocabularies`; SCC conclusion tokens absent;
  genericity token is the same VOCAB_ALIASES equivalence class as the F0 axis.
* **Binding chain** — `declared_f0_sha256` == live F0; `consistency_evidence_sha256` == live
  evidence; class-contract pointer and supplement pointer both resolve.
* **Strictness repair** — D5 whole/tail `EQUIVALENT`; `visibility.definition` `EQUIVALENT` with
  the misclassification example removed; variant SET relation `strictly WEAKER`; no residual
  asserted `STRONGER` for either repaired pair after stripping rev-notes/quoted history
  (metalinguistic-mention safe); the independent B-containment `strictly stronger` sentence is
  preserved.
* **Quantifier integrity / inflation** — every domain symbol in `statement_formal` is declared;
  shape is `forall r in D0 exists G_r comeager forall D in G_r`; predicate name resolves;
  anti_scope present; promotion rule forbids schema self-certification.
* **HF sweep** — conclusion_type is not `theorem`; no `l1_ledger_ref` in
  unresolved/contradicted state; F0 hypotheses non-empty and instantiated; unresolved items
  declared.
* **Repair delta** — token-level rev12→rev13 diff against a hash-verified third-party rev12
  snapshot: 12 changed leaf paths, **0 unexpected semantic changes** (the delta is exactly the
  documented strictness loci + binding refresh + revision metadata).

## Non-blocking findings

NF-QUANT (weighted-Sobolev threshold mentions lack an L1 anchor in the reviewed bytes; L1 item),
NF-VOC / NF-VOCGEN (canonical-vs-alias vocabulary placement; F0 literal list is the inconsistent
source under the measured rule_spec+alias policy; controller adjudication open),
NF-ACCEPT (`open dense` gate wording would accept a strictly stronger class),
NF-PRED (future-asymptotic-predictability equivalence declared UNVERIFIED),
NF-UPSTREAM (routing of HF-045-1).

## Reproduce

```bash
python3 research_map/validate_map.py
python3 artifacts/worker-045/f1_rev29_review/check_f1_rev29.py
```

`check_f1_rev29.py` is read-only on all canonical paths; it writes only `report.json`,
`controls.json` and the verdict file named by `--verdict`.

## Falsifier

Re-run the instrument at the reviewed hash: any PASS recorded here that turns FAIL, any control
that stops firing, or any reviewed input that moves falsifies this verdict. HF-045-1 specifically
is cleared by a controller/owner correction of the two F0 loci to "strictly weaker" at new pinned
hashes, or by a demonstration that the set-based reading entails the single-q tail predicate
(which would make SET the stronger reading).

## Authority limit

Worker verdict, evidence only. This record cannot set `status=done`, `validation_status=passed`,
or any gate verdict; no canonical artifact was written.
