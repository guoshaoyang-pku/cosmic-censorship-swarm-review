# W097-F2B-REV13-INDEP-REVIEW-01 — independent F2b review at rev 13

One bounded, class-bound task taken by `worker-097` (fleet instance 2026-09-12T00:56:09+08:00):
the first hash-bound, full-schema, independent verdict for **F2b / `AF-SCC-C0-VAC-GEN`** at the
live G-FORM pin.

| | |
|---|---|
| class / node / gate | `AF-SCC-C0-VAC-GEN` / `F2b` / `G-FORM` |
| reviewed artifact | `schemas/af_scc_c0_vacuum.yaml` @ `b2ab6acb2bbe…` (rev 13) |
| mirror | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` @ same sha256 (byte-identical) |
| declared F0 | `research_map/formulation_taxonomy.yaml` @ `0abb9ed8a961…` (rev 5) |
| supplement | `artifacts/formulation/formulation_taxonomy.yaml` @ `d7419b4e8963…` |
| freeze | `artifacts/formulation/FROZEN.json` rev 29 @ `815e08079aef…` |
| verdict / score | **revise / 3.0** — two hard failures, four minor advisories, controls 10/10 (erratum round 2; round 1 was 3.5/one hard failure) |
| pin drift | none (all ten pinned inputs re-measured, canonical + snapshot copies agree) |

## Result

**`.checks.H3` — internal containment-direction consistency: FAIL.**

`implication_ledger.forbidden_transfers[0].reason` (line 246) states:

> "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"

The same artifact declares the opposite containment in `implication_ledger.extension_class_containment`
(line 239): "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2", in
`one_way_entailments[2]` ("C0-inextendibility is stronger than the C2 class's conclusion"), in
`non_vacuity.vacuity_falsifier` ("a C2 result is weaker"), in
`c0_specifics.conclusion_relation_to_sibling` ("excluding all continuous extensions excludes all
C2 extensions"), and in the F2a sibling ("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of
E_C0"). The row's *conclusion* ("C2-inextendibility is strictly weaker") is correct; its *premise*
is inverted, so the forbidden-transfer rationale is self-contradictory. Recommended repair:
"strictly larger" → "strictly smaller".

This is the same defect class the rev13 repair fixed in F1 (`variant SET` direction corrected in
`VARIANT_REGISTRY.json` and the F1 strictness lines) — rev13's note for F2b says "no
class-semantics change", and the F2b inversion was left in place.

**`.checks.H3b` — live containment-denial vs asserted containment: FAIL** (added in erratum round 2).

`regularity.must_not_conflate[0]` (line 152) says "No containment with C2 or C0 is asserted here"
while the artifact asserts exactly that containment at line 239 and line 250, and the supplement's
`axis_registry` (line 145) declares the nested extension sets. The F2a sibling at line 152 marks
the identical sentence as an R2-major error. Recommended repair: adopt F2a's corrected clause.
This clause was found first by an independent peer review of the same hash
(`reviews/F2b-review-worker-018-rev13.json`); it was re-derived here from the primary bytes and
given a dedicated check before this record was re-emitted. The round-1 verdict (`revise`, 3.5)
was already correct but its hard-failure census was incomplete.

**All other hard checks pass**: H1 structure (no duplicate keys; last history entry matches
`revised_at`), H2 identity, H4 F0-binding/FROZEN-rev29 closure, H5 pointer resolution, H6
quantifier well-typedness and dual negation, H7 alias-aware vocabulary conformance, H8
canonical/mirror byte identity, H9 sibling-disjointness mutuality, H10 review-status shape.

Advisories (non-blocking): **A1** accepted alias tokens in a canonical artifact (policy: canonical
token first); **A2** `taxonomy_consistency.json` is a hash-free boolean; **A3** F0 contract text
quantifies "(s,delta)" while D0 adds the `smooth` branch; **A5** `revision_history` collapses two
revisions (documented rev12 key-collapse, same in F1/F2a).

## Prediction ledger (pre-registered vs measured)

| id | prediction | outcome |
|---|---|---|
| P1 | H3 fails with exactly one inverted statement at `forbidden_transfers[0].reason` | **confirmed** at statement level; run 1 double-listed it via two overlapping patterns, now reported as `inverted_paths` (1) |
| P2 | H1, H2, H4–H7, H9, H10 pass; H7 passes only via the alias registry | **confirmed**; H7's alias control refuted my initial vocabulary-violation reading |
| P3 | H8 passes | **confirmed** |
| P4 | A1–A4 all fire | **partially disconfirmed**: A1, A2, A3 fire; A4 does not (the `>-` fold removes the line start), an **A5** history-collapse advisory was added after run 1 |
| P5 | K1–K8 pass | **confirmed** (8/8) |
| P6 | verdict `revise`, score 3.5, one hard failure | **superseded by erratum round 2**: rounds 1–2 gave 2.5 → 3.5; an independent peer found a second hard defect (line 152 denial), re-derived here, so the final record is `revise` **3.0** with H3 + H3b |

## Controls (all pass, 10/10)

K1 H3 repair-responsiveness (repair line 246 in memory ⇒ H3 passes; baseline fails); K2 zeroed
declared-F0 hash ⇒ H4 fails; K3 unknown vocabulary token ⇒ H7 fails; K4 deleted required key ⇒
H1 fails; K5 injected duplicate `revision:` key ⇒ H1 fails; K6 diverged mirror ⇒ H8 fails; K7
determinism (identical result digests); K8 empty document ⇒ not `accept`, no raise; K9 H3b
repair-marker responsiveness.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py "$(pwd)"   # exit 0; rewrites report.json
```

`pins/` holds byte snapshots of all ten inputs with `pins/SHA256SUMS.txt`; the instrument fails
closed (exit 3, verdict `inconclusive`) on any pin drift.

## Authority and non-claims

Worker verdict only: no node status, no `validation_status=passed`, no gate verdict, no
mathematical or physical correctness decided, no citation-scope verification (L1 owns it), no
canonical write. The verdict is advisory for the controller/leads, who alone can act on it.

## Falsifier

A re-run at the same pins returning a different H3 census or verdict; a mutation control the
instrument fails to catch; or a reading showing "C2 is a strictly larger extension class" is
consistent with the artifact's own `extension_class_containment`. A later revision is a new
measurement, not a falsifier. Next falsifier: owner repair of line 246, then re-review at the new
revision.

## Files

`PREREGISTRATION.md`, `AMENDMENTS.md` (two addenda), `check_f2b_rev13.py`, `make_review.py`,
`report.json`, `report.run1_pre_amendment.json`, `report.run2_pre_erratum.json`, `REVIEW.json`,
`pins/` (snapshots + SHA256SUMS), `SHA256SUMS.txt`, `emit_events.py` (round 1),
`emit_erratum.py` (round 2), plus worker checkpoints
`runtime/state/w097_checkpoint_f2b_rev13_review.json` (round 1) and
`..._review_r2.json` (current).
