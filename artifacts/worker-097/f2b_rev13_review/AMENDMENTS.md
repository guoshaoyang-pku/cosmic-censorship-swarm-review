# Instrument amendments after run 1 (adjudicated before the amended re-run)

Run 1 (`report.run1_pre_amendment.json`, verdict `revise`, score **2.5**, hard failures
H1/H3/H5, controls 8/8) is preserved. Two of its three hard failures were adjudicated as
**false positives of this instrument**, not defects of F2b. The amendments below were made to
remove the false positives; H3 was de-duplicated but its finding stands.

## H1 — `revision 13 != len(revision_history) 11` → false positive, amended

Every rev-13 schema in the family has `revision=13` with 11 history entries
(F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe` all rev 13 / 11 entries; measured).
History entry 9 is marked `unused: true` and carries the rev-11 **and** rev-8 deltas, i.e. the
count gap is the documented rev-12 repair "duplicate revised_at keys collapsed into
revision_history". Raw `revision == len(history)` is therefore the wrong invariant for this
family. Amended H1: required keys + duplicate-key detection + `len(history) <= revision` +
indices `1..n` + well-formed entries + last entry `at == revised_at`; the gap is reported as
advisory **A5** instead of a hard failure.

## H5 — "supplement contract has neither label nor axes" → false positive, amended

The resolved object `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN`
is a real dict with `node_id: F2b`, `components`, `hypotheses`, `exclusions`, …; it simply does
not use the keys `label`/`axes` that the F0 `classes` contract uses. The pointer resolves.
Amended H5: accept any class-identity marker (`node_id` / `label` / `components.regularity_token`)
and check `node_id == F2b` when present. No shape is imposed beyond resolution.

## H3 — two matches, one statement → finding stands, deduplicated

Both inverted hits are the **same path**
(`implication_ledger.forbidden_transfers[0].reason`) matched by two overlapping patterns
(`C2\s+is\s+a\s+strictly\s+larger` and `C2[^.]{0,60}strictly\s+larger\s+extension\s+class`).
Prediction P1 ("exactly one inverted statement") is confirmed at statement level; the census now
reports `inverted_paths` (distinct statements) alongside every pattern match.

## Effect

Amended expectation: H3 is the only hard failure ⇒ `revise`, score **3.5**, matching P6.
Controls K1–K8 are re-run unchanged. This amendment is an instrument correction, not a
re-measurement: no pinned input byte changed (`pin_drift` was and remains empty).

---

# Addendum 2 — erratum round 2 (post-publication, same pinned bytes)

Round 2 (`report.run2_pre_erratum.json`, verdict 3.5, hard H3 only) was emitted as the round-1
deliverable set. Shortly after, an independent peer review of the **same** F2b rev13 hash
(`reviews/F2b-review-worker-018-rev13.json`, verdict revise 3.0) reported a second hard failure
this instrument did not test: `regularity.must_not_conflate[0]` (line 152) carries the live denial
"No containment with C2 or C0 is asserted here" while the artifact asserts that containment at
line 239 and line 250, and the supplement's `axis_registry` (line 145) declares the nested
extension sets.

Re-derived here from the primary bytes: the denial is unmarked (no repair note), the F2a sibling
at line 152 marks the identical sentence as an R2-major error ("the earlier 'no containment with
C2 is asserted' was wrong"), and supplement line 195 records H2_loc ⇒ C2. The round-1 review was
therefore **incomplete**, not wrong: its verdict was already `revise`.

Amended instrument: new hard check **H3b** (live containment-denial vs asserted containment;
clauses carrying an explicit repair marker are treated as historical notes, so the check stays
false-positive-safe if the owner adopts F2a's repaired wording) and control **K9** (repair-marker
responsiveness of H3b). Amended verdict **3.0** with H3 + H3b as two hard failures, per the
pre-registered score rule (two hard failures ⇒ 3.0). Controls 10/10.

No pinned input byte changed. The round-2 record (`report.run2_pre_erratum.json`,
`REVIEW.json` sha `1bb9dff017a20866…`) is preserved; round-2 events remain in the outbox and are
superseded by the erratum events emitted by `emit_erratum.py`.

