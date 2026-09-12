# W078-GF0-CRITERIA-AUDIT-01 — independent audit of the G-F0 gate criteria

Worker: `worker-078`. Node/gate: `F0` / `G-F0`. Classes:
`AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH`.
Started 2026-09-12T00:44+08:00. Read-only on every canonical path.

## Why this task

`research_map/research_map.json` (pass `astra-lifecycle-04`, 00:37:18) holds all five gates at
`pending`; its G-F0 audit reason recorded **0 distinct accept reviewers** at the current F0 hash
and the gate's `unmet` list still cites a superseded hash (`66bf917bd368`). Between 00:37 and
00:44 a re-review round landed accepts at the current hash; the map was then rewritten at
00:43:08 and now records 4 distinct accepts for G-F0, while `unmet[0]` still cites the superseded
hash and the gate verdict stays pending. G-F0 is the only gate whose two-reviewer criterion is
met at its current measured hash, and it is the top of the dependency chain (G-AUDIT's A1
coverage needs two accepts for F0/F1/F2a/F2b/L0). This audit adds a fifth independent accept and
checks the criterion clauses directly.

This audit checks the gate's own criterion text, nothing else:

> `formulation_taxonomy.yaml exists; exactly 4 separate class ids; disjointness tests;
> 2 independent reviewer verdicts`

## Method (pin-then-verify, drift-voiding)

1. Byte-exact snapshot of the canonical artifact at run start
   (`snapshot/formulation_taxonomy.0abb9ed8a961.yaml`) plus the companion authoring supplement
   (`snapshot/formulation_taxonomy_supplement.d7419b4e8963.yaml`). All checks run against the
   pinned bytes; the live path is re-measured at the end of the run.
2. Twelve checks (A1, B1–B3, C1–C3, D1, E1–E2, F1, G1), implemented independently; the harness
   does not call the controller's lifecycle tool for its primary verdict.
3. **Discriminating controls** (G1): four targeted perturbations of the pinned document —
   dropped disjointness pair, fifth class id, blanked separation argument, unknown axis token —
   must each be rejected by the corresponding check. All 4/4 are rejected, so the checks are
   not a rubber stamp.
4. **Pinned test–retest**: the harness was run twice on identical bytes; after removing the
   timestamps the two reports are byte-identical (`report.json` vs `report_rerun.json`).
5. Reviewer criterion (E1) is recomputed from `reviews/*.json` by an independent implementation
   of the coverage rule (target normalisation, explicit pin fields only, `counts_as_full_schema_verdict`
   flag); E2 then cross-checks that result against `astra_lifecycle.review_coverage`, a different
   code path, on a freshly measured map — both mechanisms agree.

## Result — `accept_with_notes` (11 PASS / 1 WARN / 0 FAIL)

| check | status | result |
|---|---|---|
| A1 identity | PASS | live canonical == snapshot == `0abb9ed8a961…` (start and end of run) |
| B1 four class ids | PASS | exactly the 4 frozen ids, in order, each with a descriptor, no extras |
| B2 descriptor fields | PASS | all four descriptors expose family / matter_model / symmetry / conclusion_type |
| B3 no fifth class token | PASS | 4 distinct `AF-*` tokens document-wide, all within the frozen four |
| C1 disjointness pairs | PASS | 6/6 unordered pairs, each exactly once, non-empty decisive_axes and separation |
| C2 axis vocabulary | PASS | all decisive_axes resolve in the declared 8-axis field_vocabulary |
| C3 merged-regularity guard | **WARN** | no merged class token; one prose hit, see note N2 |
| D1 supplement class set | PASS | companion supplement `frozen_classes` and `class_contracts` both equal the canonical four |
| E1 independent verdicts | PASS | **4 distinct full-accept reviewers** at `0abb9ed8a961`: deepseek-flash-18, deepseek-flash-19, worker-025, worker-038 |
| E2 controller cross-check | PASS | controller `review_coverage` reports the same 4 reviewers, `two_distinct_accepts=true` |
| F1 named blockers | PASS (reported) | canonical `status: draft_unverified`; genericity questions Q1/Q3 still owned by F1/F2 |
| G1 controls | PASS | 4/4 perturbations rejected |

### Notes (non-blocking, reported for the gate owner)

- **N1 — the gate's unmet list is stale.** The 00:43:08 map now records four distinct accepts at
  the current hash, but `gates[G-F0].unmet[0]` still cites `66bf917bd368`, a superseded revision.
  A lifecycle pass re-run at these hashes should reconcile the unmet list; only the controller can
  move the gate verdict.
- **N2 — prose notation hygiene.** Line 15 of the canonical taxonomy reads
  `(h) C2/C0 provenance.schema_owner pointers …`. The frozen validator's own regex
  (`artifacts/worker-01/validate_taxonomy.py`: `MERGED_RE = C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0`)
  matches this string. The match is **not** a class token: the class ids, descriptors, transfer
  rules and guards all keep C2 and C0 separate (B1/B3/D1 pass independently, and a class-token
  scan for `AF-SCC-C{0/2,2/0}` and for a merged `regularity_token` value is clean). Recommend
  rewriting the phrase as “the C2 and C0 provenance.schema_owner pointers” at the next revision.
  Flagged WARN, not FAIL, because the gate criterion is about class separation, and separation
  is intact; a checker that applies the frozen regex to prose without a class-token position
  test would report a false merge here.

## Falsifiers

1. Re-measure `research_map/formulation_taxonomy.yaml`: a hash other than
   `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` voids the binding of this
   audit to that revision (it does not refute the checks for the pinned bytes).
2. Re-run `audit_gf0_criteria_078.py --pin 0abb9ed8a961…`; any failed check, or a report that is
   not identical to `report.json` modulo timestamps, falsifies the verdict.
3. Exhibit a fifth class id or a merged regularity **class token** in the pinned bytes; or show
   that one of the four descriptors or one of the six disjointness pairs is absent/malformed —
   any of these falsifies B1/B2/C1.
4. Show that two of the four accepting reviewers are not independent (same author/provenance,
   or a shared undisclosed draft), or that a later review at the same hash supersedes one of
   them; that falsifies E1 and the “two independent reviewer verdicts” criterion.
5. Show that `status: draft_unverified` or the unresolved genericity ownership blocks G-F0 by
   the gate's own criterion — the criterion text does not say so, but the lead/controller may
   rule otherwise; such a ruling would supersede note N1.

## Limits / non-claims

- Not a controller gate verdict; only the controller/group lead can set `G-F0`.
- Does not re-derive the physics, truth or non-vacuity of the four class contracts, and does not
  verify the literature pointers, which remain `UNRESOLVED` in the file's own provenance block.
- Reviewer independence is measured as distinct reviewer id + full-verdict flag; this is the
  controller's own coverage rule, not a provenance audit of the four reviewers.
- The C3 note is a notation finding; it changes no class id and no disjointness row.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-078/f0_criteria_audit/audit_gf0_criteria_078.py \
        --pin 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3 \
        --json artifacts/worker-078/f0_criteria_audit/report.json
```

Artifacts (sha256 in the event stream and the checkpoint):
`audit_gf0_criteria_078.py`, `report.json`, `report_rerun.json`,
`snapshot/formulation_taxonomy.0abb9ed8a961.yaml`,
`snapshot/formulation_taxonomy_supplement.d7419b4e8963.yaml`.
