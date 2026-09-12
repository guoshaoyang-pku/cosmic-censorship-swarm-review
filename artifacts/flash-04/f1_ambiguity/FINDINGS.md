# F1 ambiguity attack — findings

| field | value |
|---|---|
| assignment | `asg-2026-09-11-F1-deepseek-flash-04-13` (node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`) |
| artifact | `schemas/f1_falsifier_tests.jsonl` — 17 tests, sha256 `18102c206ab23b489a7c2132a83fe1bc99e0f70357f7e71de0efaba8ca64c4ce` |
| runner | `artifacts/flash-04/f1_ambiguity/run_f1_ambiguity.py` |
| bound schema | **frozen rev4** `artifacts/formulation/schemas/af_wcc_vacuum.yaml`, sha256 `f512af5f4db39b029fdfe900699d69fa4d9220f75080faf9713006321309381c` |
| frozen snapshot | `artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f512af5f.yaml` |
| status | **unverified draft; no node completion claimed** |
| author | `deepseek-flash-04` (DeepSeek Flash breadth executor) |

## 0. Frozen rev4 delta — current state (authoritative)

Lead-formulation froze F1 revision 4 and ruled on every finding
(`artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md`). The frozen
pin is `artifacts/formulation/FROZEN.json`; the 23:33:37 message cited
`17873b9d…`, which the manifest superseded at 23:35:45 with `f512af5f…`. This
suite is rebound to the manifest hash.

| id | delta | disposition |
|---|---|---|
| AMB-09 | **closed** — `genericity.ambient_space_is_data_space: true` | ruled: ambient space is the data space |
| AMB-10 | **closed** — canonical `residual_comeager` | `VOCAB_ALIASES.json` accepts `baire_residual` as an alias |
| AMB-07 | **finding closed** — `genericity.membership_ruling` added | ruled: membership is set-level only; individual datum membership is not decided by design, and symmetric data are expected outside G as a proof obligation |
| AMB-08 | **finding closed** — `topology.slice_topology` narrowed | frozen rev4 admits only slices diffeomorphic to R³ (one AF end); the r3 breadth decision is reverted |
| AMB-01 | reclassified | accepted obligation: non-vacuity witness membership is UNVERIFIED |
| AMB-02 | reclassified | accepted obligation: meagerness of excluded families is UNVERIFIED |
| AMB-03 | reclassified | accepted obligation: the closed-proper-subspace/Kerr meagerness step must be stated |
| AMB-15 | reclassified | accepted obligation: equivalence to future asymptotic predictability is UNVERIFIED, L1 owns it |
| AMB-04, AMB-06 | renamed | fields moved in rev4; both remain decided |
| other 7 rows | unchanged | decided controls/classifications |

Counts: closed 2, finding-closed 2, reclassified 4, renamed 2, unchanged 7;
**4 still open** (`AMB-01, 02, 03, 15`). Machine-readable:
`frozen_rev4_delta_report.json`.

Adjudication-queue cross-check against `adjudication_queue.open_rows`:
3 rows queued, 2 exact + 1 alternate `deciding_leaf` match, 0 mismatch.
**`AMB-03` is accepted in the adjudication doc but absent from `open_rows`** —
the queue is incomplete. The queue's fourth `unresolved_items` entry (the
diffeomorphism-quotient technical gap) is not probed by any suite row; it is
flagged for A1 rather than silently skipped.

Manifest hygiene: `FROZEN.json` lists its own sha256 as `94880c36…`, which can
never match its content (`8d0725ef…`) because the manifest embeds its own hash.
The other 14 entries verify. Reported as a blocker item, not used as evidence.

---

## 1. Headline result (r3 worker draft — historical)

The suite answers, for each probe: is the datum in `AF-WCC-VAC-GEN`, does the F1
class conclusion hold, and **which schema field decides**. The declared falsifier
of the assignment — "a test that no schema field can decide" — is reported
honestly below.

## 1. Headline result

Against revision 3 (`7a3e1f93`):

* **11 / 17** tests have a determinate deciding value and no matching entry in the
  r3 schema's own `unresolved` list (frozen rev4 result: **13 / 17**).
* **6 / 17** are structurally open: `F1-AMB-01, 02, 03, 09, 10, 15`.
* **8 / 17** remain review findings (non-`decided` strength): the six structural
  ones plus `F1-AMB-07` (interpretation undeclared) and `F1-AMB-08` (slice topology
  admitted by decision, but constraint solvability on admitted topologies is not
  decided by any field).
* **42 / 42** FORM-RULE-SPEC R01–R15 leaves are present under their exact contract
  names (0 missing, 0 needing an alias). This is the strongest single improvement
  over revision 2.
* The declared falsifier **did not fire** on revision 3. It **did fire on
  revision 2** (`f15ea523`): R08's `non_vacuity` block was absent and
  `conclusion.conclusion_type` did not exist under its R11 name.

## 2. Review findings (revision 3)

| id | deciding field | finding | schema's own stance |
|---|---|---|---|
| AMB-01 | `non_vacuity.condition` | non-vacuity condition excludes the Minkowski-only reading, but no witness is filed; the class conclusion must not be called non-trivial | declared unresolved (`non_vacuity.witness`) |
| AMB-02 | `genericity.excluded_set` | type-II critical threshold data are named as candidate `E_gen` members and tier-1 falsifiers must be robust; critical collapse is therefore outside the quantified domain **if** the family is meagre | declared unresolved (`genericity.kind_and_ambient_space`) |
| AMB-03 | `genericity.generic_set` | finite-dimensional Kerr is outside `D_gen` via the standard closed-proper-subspace argument, a step the schema does not state | declared unresolved (genericity) |
| AMB-08 | `topology.slice_topology` | F1 r3 admits any connected complete one-ended asymptotically flat slice by decision; whether vacuum constraint data exist on every admitted topology, and whether the class requires solvability there, is not decided by any field | structural value determinate; breadth review |
| AMB-07 | `class_components.symmetry` | three symmetry slots say `none_assumed`, all class-level; **no field excludes or admits a single symmetric datum**, and symmetry is absent from `unresolved`. AMB-04 and AMB-07 still get opposite membership verdicts under the two readings | **undeclared gap** |
| AMB-09 | `genericity.ambient_space` | `D_w` + `H^4_{1/2+eps}` norm topology fix the data-space reading, so the data-vs-development objection does not change membership; the genericity proposal remains unreviewed | declared unresolved (genericity) |
| AMB-10 | `genericity.kind` | contract slot uses the R07 token `residual_comeager`; `class_axes.genericity_kind` keeps the F0 token `baire_residual`; `vocabulary_alignment` reconciles `conclusion_type` only. Two checkers read the same class differently | declared unresolved (genericity) |
| AMB-15 | `conclusion.equivalence_claim` | revision 3 now owns the equivalence question with status `unverified`; the F0 geodesic phrasing is kept in `variants`; no equivalence proof exists | explicitly `unverified` |

`AMB-07` is the sharpest finding because it is the only one the schema does not
already flag. It is a one-line fix (a datum-level symmetry clause plus a decision
on whether symmetric instances are excluded) or an explicit ruling that
`none_assumed` is class-level only and symmetric data are admitted.

## 3. What revision 3 closed (found against revision 2)

* R08 `non_vacuity` block added, with `witness_status: unresolved` rather than an
  invented witness.
* R01–R15 contract leaves restructured to exact names; the R11
  `conclusion.conclusion_type` collision resolved and documented in
  `vocabulary_alignment`.
* `topology.slice_topology_class_decision`: non-R³ interior topology admitted by
  decision (AMB-08 becomes decidable on the topology question, but the suite keeps a
  breadth finding: constraint solvability on admitted topologies is unaddressed).
* `data_class.adm_mass_class_decision`: no strict lower bound `E > 0`; negative
  mass excluded by `E >= |P|` (AMB-04).
* `visibility.curve_class` and `visibility.set_vs_point`: geodesic and
  single-point readings pinned as class decisions (AMB-11, AMB-17).
* `premise.future_boundary_class_decision`: visibility is stated against the
  conformal boundary of the asserted completion (AMB-12).

## 4. Cross-check against F1's own `adjudication_queue`

The schema author consumed an earlier 16-test version of this suite and recorded
per-probe decisions in `adjudication_queue`. `audit_adjudication_queue.py` compares
that block (in the frozen snapshot) with the current 17-test suite:

* 10 of 17 tests appear in the queue; no queue-only entries, no duplicates;
* 5 exact `deciding_leaf` matches, 1 match via an alternate, 4 multi-field
  attributions differ (`AMB-02, 09, 10, 13`) — the queue should carry both leaves;
* 7 tests are absent from the queue. Five are controls or decided rows
  (`AMB-05, 06, 12, 14, 17`); two are live findings that A1 should receive:
  **`AMB-03`** (Kerr/non-generic meagreness) and **`AMB-15`** (the unverified
  equivalence). The queue's own note calls `AMB-15` its single open probe, yet
  `AMB-15` is not in the item list — an internal inconsistency in the queue.
* The queue's decision for `AMB-07` closes the *interpretation* gap by ruling that
  symmetric data are admitted ("not assumed but also not forbidden"); this is a
  documentation-level decision pending A1, not yet a normative field.
* The queue's `AMB-10` entry answers the semantic transfer question but does not
  reconcile the `baire_residual` / `residual_comeager` token duality, which
  reviewer 17's addendum independently flags as a major finding.

Cross-check artifact: `adjudication_crosscheck.json`.

## 5. Bundle revision

After the first emission (23:30) a self-review found five rows whose yes/no answers
overstated what the schema decides (`AMB-02, 03, 08, 09, 13`). They were corrected,
the artifact was rebuilt (`106cf329`), and superseding outbox events with
`supersedes` links were emitted (23:31). The earlier events remain in the stream as
history; only the latest artifact hash should be reviewed.

## 6. Schema-hash drift (process finding)

The same declared `revision: 3` was observed at several content hashes while this
suite was being written:

| observed sha256 (prefix) | state |
|---|---|
| `f15ea523` | revision 2 (23:26) |
| `f55722a7` | revision 3 first read (23:34) |
| `a7ef0398` | revision 3 amended mid-audit |
| `7a3e1f93` | revision 3 settled; **the hash this suite is bound to** |

G-FORM's acceptance criterion is "reviewers 17,18 accept with cited sha256", so a
revision number alone cannot identify what was reviewed. Every verdict on F1
should cite a content hash, and this suite should be re-run whenever the hash
changes. The runner records `schema_drift` when `--expect-sha` does not match the
document it bound. Revision 2 (`f15ea523`) was superseded before a
snapshot could be taken, so the r2 falsifier observation is documented in the
superseded outbox events and in the session record but is **not independently
replayable from this bundle**. The preserved `f55722a7` snapshot is the *r3 first
read*: replaying it (`r3_f55722a7_replay_report.json`) shows 11 open rows against
the 6 on settled r3, which documents the amendment trajectory. The r2-era binding
pass is kept in `build_tests.py` as `SCHEMA_BINDING_R2_SUPERSEDED` for provenance.

## 7. What this is not

* Not a physics verification and not a literature check: every literature pointer
  in the suite is `unresolved_pending_L1`.
* Not a node completion: the artifact is `unverified`; `F1` stays `active`.
* Structural binding only: a determinate field value can still be semantically
  insufficient, which is why non-`decided` rows remain findings.
* Not a review: the runner self-test validates the runner, not the schema.

## 8. Next falsifiers

1. Lead-formulation/A1 adjudicates the seven findings; if any is rejected as
   wrong, the deciding-field mapping is falsified and must be corrected.
2. Freeze F1 and cite a sha256 in the G-FORM verdict; re-run this suite against
   that hash with `--expect-sha`.
3. Close AMB-07 (encode the recorded admission of symmetric data in a normative
   field, not only in `adjudication_queue`) and AMB-08 (state whether constraint
   solvability is required on every admitted topology); add `AMB-03` and `AMB-15`
   to the queue and name both leaves for the four mis-attributed rows; then re-run
   and expect the finding list to drop.
4. Reconcile the genericity token sets (F0 `baire_residual` vs R07
   `residual_comeager`) with a mapping or a single frozen vocabulary.
5. File a non-vacuity witness artifact; then AMB-01's unresolved entry can be
   falsified.

## 9. Reproduce

```bash
cd artifacts/flash-04/f1_ambiguity
python3 run_f1_ambiguity.py --validate-only
python3 run_f1_ambiguity.py --self-test
python3 run_f1_ambiguity.py --schema schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml \
    --expect-sha 7a3e1f93 --out ambiguity_report.json     # exit 1 = open findings
python3 build_tests.py                                     # regenerate the JSONL
```

Exit codes: `0` structurally bound, `1` open findings (expected here), `2` suite or
runner invalid, `3` configuration error.
