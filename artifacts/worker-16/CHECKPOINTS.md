# worker-16 checkpoints (deepseek-flash-16)

Session start 2026-09-11T23:15:11+08:00; assignment deadline 2026-09-12T03:15. Node bindings:
A1 (calibration proposal), A0 (assigned rubric draft), F1/F2 (assigned independent reviews),
L0 (assigned conditional-claim review). No node completion claimed at any checkpoint.

## CKPT-0 — 23:19:25 — recon, no assignment
- Read HANDOFF.md, README.md, research_map.json, ASTRA_HANDOFF.md, ARCHITECTURE.md, comms/PROTOCOL.md.
- `comms/inbox` empty at 23:19:25; map VALID; 10/10 declared artifacts missing; F0/A0 done with no artifact.
- Emitted proposal + blocker events; first `status` event rejected (`status` must be a node status), fixed.

## CKPT-1 — 23:22:11 — A1 calibration proposal support frozen
- `artifacts/worker-16/audit_calibration/`: 10 labeled maps, signature scoring, live-map coverage probe.
- Detector `c4769b99`: FP=0, FN=3, TP=2, TN=5; findings F1 (failed gate swallowed), F2 (class_id not
  whitelisted), F3 (negation laundering), C1 (0/10 nodes carried class_id). AT1 determinism PASS.

## CKPT-2 — 23:27 — A0 assignment executed (draft, not canonical)
- Assignment `asg-2026-09-11-A0-deepseek-flash-16-25` ack'd at 23:25; owner published their own
  canonical rubric at ~23:24, replacing this worker's canonical write. Decision: do not race; submit
  a merge candidate from `artifacts/worker-16/a0_rubric/`.
- Merge candidate `0fda6c21`: PASS V1–V7, 33/33 acceptance lines name an evidence type, 14 evidence
  types, HF-01..17, gate→task_type map, no universal scalar score. Owner canonical at the time
  (`25808142`): FAIL, 32 gaps. Later canonical revisions (`d748a9e3`) still FAIL the same checks.

## CKPT-3 — 23:39 — two assigned A1 reviews
- **F1** `schemas/af_wcc_vacuum.yaml`: verdict revise, score 3.0. Reviewed the map-pinned r3
  `f55722a7` in full; recorded a process-critical drift chain (`f15ea523 → f55722a7 → a7ef0398 →
  7a3e1f93` under one revision label). Findings: unverified equivalence inside the statement;
  non-vacuity imports a black-hole region; tier_1 falsifier stronger than the statement;
  machine_checkable_steps overstate decidability; exact_quantifiers pinned while domains are
  proposals. Drift blocker emitted.
- **F2b** `schemas/af_scc_c0_vacuum.yaml`: verdict revise, score 3.0 on `0150bfdf`. Major finding:
  the genericity transfer witness "open dense does not imply comeager" is false (open dense sets are
  comeagre; the failed direction is comeagre→open-dense, e.g. R\Q). Secondary: H2_loc containment
  tension, topological-vs-smooth M', decay/Sobolev reconciliation, missing symmetry slot, PMT locator.

## CKPT-4 — 23:45 — recalibration delta + F1 delta recheck
- Detector `6873cb51`: recalibrated corpus (13 fixtures). Fixed since CKPT-1: unknown class token,
  artifact merge scan, new frozen-artifact drift/missing checks. Open: R2-1 (failed gate swallowed),
  R2-2 (negation laundering), R2-3 (statement-mode FP). Live map informational: 6 soft unknown-class
  tokens in `ledger/theorems.jsonl`.
- F1 delta recheck on the now-stable `7a3e1f93`: verdict revise (same reviewer, not a second
  independent verdict); drift resolved as history; dangling-refs finding resolved-by-decision;
  major equivalence finding unchanged.

## CKPT-5 — 23:51 — L0 conditional-claim review
- Claim `lit-20260911-012` (linked T-301): verdict revise, score 3.5. Verified against fetched
  abstracts of arXiv:1710.01722, arXiv:2104.08222, arXiv:2205.14808. The conditional is stated
  verbatim in the source and Kerr stability is not asserted (clean); the AF-SCC-C0-VAC-GEN binding is
  not supported as stated (interior data + deferred retrieval), the qualifier "appropriate" is
  dropped, the weak-null-singularity/revised-SCC caveat is omitted, the partial antecedents are
  weaker than stated, and SRC-035 (Λ>0) is a scope leak in the evidence set.

## CKPT-6 — 00:15 (next day) — F2b delta recheck + candidate detector patch
- F2b `0a4ceac5` (revision 3): my major finding was adopted — the transfer table now has
  `residual_comeager → open_dense_escape: no_transfer` (R\Q witness) and
  `open_dense_escape → residual_comeager: entails`; extension now on a smooth M'; PMT flagged.
  Remaining: F2b-16-02 (H2_loc containment tension). Verdict revise, score 4.0 (same reviewer).
- Candidate patch `detector_fixes.patch` (`2b81b446`) staged under `proposed/` + my artifact dir,
  shared `research_map/` untouched. Verification: worker-16 corpus live FP=1/FN=3 vs proposed
  **FP=0/FN=0 (exit 0)**; worker-07 registered 27-fixture regression PASS on both. Applies cleanly
  with `patch -p1`.

## Standing rules
- Shared paths (`research_map/`, canonical artifacts, `schemas/`, `ledger/`, `numerics/`, `reviews/`
  only where assigned) are never edited without an assignment; support work stays under
  `artifacts/worker-16/` or `proposed/`.
- Every result pins the input hash; a changed input invalidates the result instead of silently
  updating it. A review verdict applies only to the hash it cites.

## CKPT-7 — 00:10 (next day) — FORM-HELDOUT-08 second held-out corpus, measurement complete
- Assignment `assign-FORM-HELDOUT-08-2026-09-11T23:52:35+08:00`: node A1, gate G-CLASSBIND,
  class_ids AF-WCC/C2/C0-VAC-GEN, budget 3.0 h, stop_rule one complete held-out report.
- **Frozen binding.** The live canonical schemas were rewritten at 00:08–00:09, after FROZEN rev19,
  so the revision-13 hashes named by the assignment were no longer on disk. Located byte-identical
  rev13 copies in worker-11's snapshot (`artifacts/flash-11/f1_aux_class_binding/corpus/canonical/`:
  af_wcc `f962c117`, af_scc_c2 `e9fcefe6`, af_scc_c0 `bdb23f76`), copied them to
  `heldout2/bases/` and built only against those. flash-17's blocker
  `flash-17-blocker-freeze-drift-20260912T001054` already covers the live-path drift; FROZEN rev20
  later re-pinned the live files. Corpus stays on rev13 per the assignment; no rebound verdicts.
- **Corpus** (`heldout2/`): 29 mutants / 21 families / 22 rephrased, deterministic builder
  `build_corpus.py` `da83817e3467`, manifest `1c8fa8888226` hashed before any stage run, no fixture
  rewritten after a verdict. Axes deliberately avoid R26–R31 (assumption-axis drift, formal-vs-ordered
  inconsistency, containment reversal, equivalence inflation, status/provenance honesty, guard erasure).
- **Result** (`report.json` `87f204918003`, valid=true): structural escape **1.0**, semantic escape
  **1.0**, union escape **1.0** — 0/29 caught, 21/21 families escape. Controls 7/7 accepted by both
  stages (3 frozen canonical + 2 conforming + 2 negated-phrase). Positive control
  `gate_sensitivity_check.json`: 6 known FORM-HELDOUT-07 leaks are still rejected by the same gate, so
  the pipeline is live. Raw per-fixture verdicts in `raw_verdicts.json` `84c1b87953f5`.
- No node completion claimed; the 21 escaped families are the deliverable per the assignment falsifier.
- Next: independent post-run leak-validity review, then upward artifact events and controller checkpoint.

## CKPT-8 — 00:36 (next day) — independent review, comms accepted, controller checkpoint
- Independent post-run adversarial review (`heldout2/leak_validity_review.json` `b2623a5dc459`, reviewer
  `independent-subagent`, gates not re-run): **25/29 genuine class-level leaks, 0 legitimate, 4 borderline**
  (m11 development-topology, m19 known-obstruction-omitted, m26 WCC visibility negation, m27
  schema-falsifiers-erased). The 4 borderline mutants are still defects a reviewer should flag (false
  disclaimer, dangling reference, re-opened R1 F02 conflation, guard erasure) but are not clean class
  changes; the review is post-hoc and does not alter the frozen verdicts (all 29 escaped both stages).
  Strongest escapes named by the reviewer: m01 excluded-set, m09 equation-axis, m16 containment reversal,
  m22 epistemic-status inflation, m25 WCC completeness swap, m28 ambient-space collapse.
- Emitted 5 `artifact` events to `comms/outbox/worker-16.jsonl` (report, manifest, gate-sensitivity
  control, drift addendum, leak-validity review); schema-validated before append.
- `python3 research_map/checkpoint.py --label form-heldout-08` → `ckpt-20260912-001530`: accepted 5,
  rejected 0; map VALID; evidence hard failures 0; classsep regression PASS (17/0/10/0).
- FORM-HELDOUT-08 done per stop_rule ("one complete held-out report"). No node completion claimed.

## CKPT-9 — 00:25 — W16-F0-INDEP-REVIEW-01 (independent F0 review, G-F0)
- Bounded class-bound task self-claimed: no worker in the 00:12/00:16 fleet had an independent
  full-schema F0 review; controller gate audit at 00:19:58 recorded G-F0 = 0 accepts at
  `276009f4f63d`. Target reviewed at that pinned hash (equals FROZEN rev25 + artifact registry).
- Verdict **revise, score 3.5**, 3 blocking findings: B-16F0-1 D1 set-based `J-(I+)` reading still
  used in the `AF-WCC-SCALAR-SPH` conclusion (line 406, verbatim the line-75 demoted text);
  B-16F0-2 D3's "explicit comeager in each class" is absent there (line 405); B-16F0-3 C2/C0
  `schema_owner` point at `schemas/af_scc_regularities.yaml`, map-recorded in `legacy_artifacts`
  as a non-class aggregator, under the superseded node name `F2`.
- Checker `check_f0.py`: 18 checks → 13 PASS / 3 FAIL / 2 NOTE. Controls: P1 repaired fixture →
  0 FAIL (16 PASS/2 NOTE); N1 wrong pin → exit 2, no results file. This is what makes the three
  FAILs attributable to the defects rather than checker over-firing.
- Emitted 9 schema-validated events to `comms/outbox/worker-16.jsonl` (status claim, formal_model
  claim, 5 artifacts, review, checkpoint status); re-run of the emitter appends 0 (idempotent).
  All 9 are present in the accepted stream `research_map/events.jsonl`; 0 of them rejected.
- `python3 research_map/checkpoint.py --label w16-f0-indep-review-01` → `ckpt-20260912-002510`:
  map VALID; comms accepted 0 / duplicates 1580 (events had already been ingested) / rejected 0;
  1 evidence hard failure, the pre-existing adjudicated CF-16 `claims[36]` false positive.
- Artifacts + sha256: `reviews/F0-review-16.json` `b6c919581ae1`, `check_f0.py` `59ac0f1c6225`,
  `check_results.json` `db229b6ec6aa`, `controls.json` `88452d2dae22`, `REPORT.md` `e48e5da65b05`.
- No node completion and no gate verdict claimed (worker authority). Falsifier: quote the pinned
  bytes to show the attributed reading is absent, or show `af_scc_regularities.yaml` is canonical.
  Next: lead disposes B-16F0-1/2/3, re-runs the checker to 0 FAIL at the new hash.


## CKPT-10 — F0 mirror-conflict independent verification (W16-F0-MIRROR-VERIFY-01)
- Self-claimed bounded task: no unclaimed worker-016 assignment; verified the evidence behind `leadform-blocker-0007` instead of duplicating any prior pass.
- Verdict **CONFIRMED** on artifacts/formulation/evidence/f0_mirror_conflict.json#sha256:7e3a7bc89a75: canonical `276009f4` (35145 b) vs authoring `c8e979a1` (20937 b) are two different artifacts; staged substitutions crash with `KeyError: 'class_contracts'` / `KeyError: 'class_ids'`; control exits 0 CONSISTENT; FROZEN rev26 pins both; all three schema pointers resolve only in the supplement.
- 13 PASS / 2 INFO / 0 FAIL with positive and negative controls. Two INFO findings: accept coverage at the canonical hash (evidence_refs-bound accept not counted by the 00:24:40 scan) and superseded lineage `565a6e505188`.
- Artifacts: `f0_mirror_check/verification.json` `f1fd27367547`, `verify_mirror_claim.py` `49e2f1c70c63`, `REPORT.md` `7ad6514407d5`. Read-only on all repo artifacts; no node completion or gate verdict claimed. REC-1/REC-2 stays controller authority.
- Emitted 7 new outbox events (idempotent re-run appends 0).

## w16-ckpt-r03-adj-01 — 2026-09-12T00:46:41+08:00
- task W16-R03-ADJ-01 (F1, AF-WCC-VAC-GEN, G-FORM), self-claimed, 0.5 h
- adjudication: literal-match false positive (R03 implementation), with a real corpus-convention deviation
- frozen F1 cce9c60146d6 unchanged; stage2 reject R03 only; V1 render accept; patched tool accept at unchanged doc_sha256; V4 still reject
- checkpoint: `runtime/state/w016_checkpoint_r03_adjudication.json`; events: 11 (11 appended)
- W16R28-F1/F3/F4 remain open and are not addressed here

## w16-ckpt-r03-adj-01 — 2026-09-12T00:47:09+08:00
- task W16-R03-ADJ-01 (F1, AF-WCC-VAC-GEN, G-FORM), self-claimed, 0.5 h
- adjudication: literal-match false positive (R03 implementation), with a real corpus-convention deviation
- frozen F1 cce9c60146d6 unchanged; stage2 reject R03 only; V1 render accept; patched tool accept at unchanged doc_sha256; V4 still reject
- checkpoint: `runtime/state/w016_checkpoint_r03_adjudication.json`; events: 11 (0 appended)
- W16R28-F1/F3/F4 remain open and are not addressed here

## w16-ckpt-f2b-rev29-adj-01 — 2026-09-12T01:17:20+08:00
- task W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01 (F2b, AF-SCC-C0-VAC-GEN, G-FORM), self-claimed, 0.6 h
- pinned: F2b `b2ab6acb2bbe` / F2a (sibling control) `e9a27996dfd3` / FROZEN rev29 `815e08079aef` / F0 `0abb9ed8a961` / VOCAB `46cd9f1eb534`; all measured == declared
- findings: **H1 CONFIRMED** (line 246 calls C2 the "larger" extension class vs the file's own E-nesting and the corrected C2 sibling); **H2 CONFIRMED** (line 152 denies H2_loc containment against its own ledger; worker-16 `F2b-16-02` self-correction disclosed); **H3 CONFIRMED-IN-CANDIDATES** (circulating repairs 84b5d3fa/98f9ec83 reverse the H2_loc entailment — class-relative control: true in C2, false in C0; independently reproduces worker-029 `W029-R7-H2`); **V1 CONFIRMED-DIVERGENCE** non-blocking (separate F0/VOCAB single-sourcing ruling pending)
- repair adequacy: `corrected_51c253c4` and `nesting_4951cc96` finding-free under the checker; no candidate re-stamps V1; no formal-field changes in any candidate
- controls: 9/9 pre-registered evaluations hold (frozen/null fire H1+H2, circulating fire H3, landable clean, 3 synthetic discrimination controls); checker exit 0; 18 adverse verdicts censused at the pin
- artifacts (`artifacts/worker-016/f2b_rev29_containment_adjudication/`): `results.json` `b6e16f68999f`, `REPORT.md` `477548001487`, `cluster_table.json` `a4dfa881671d`, `adjudicate_f2b_containment.py` `6aed14ac8368`, `manifest.json` `547ce3d468c0`
- events: 11 emitted (10 + 1 erratum for checkpoint/manifest ref stability), all 11 accepted, 0 rejected; emitter re-run appends 0
- worker checkpoint `runtime/state/w016_checkpoint_f2b_rev29_adjudication.json` `5c20f7fca529`; controller checkpoint `ckpt-20260912-011720`: map **VALID**, accepted 6 / duplicates 7018 / rejected 1 (worker-036 `conclusion_type`, not this task), classsep regression PASS 17/0/10/0, evidence hard failures = the two pre-existing adjudicated CLASSSEP `claims[36]`/`claims[94]`
- path note: this slot's earlier history is under `artifacts/worker-16/`; this task's deliverables are under `artifacts/worker-016/` and all events cite the latter consistently
- no node completion, no gate verdict, no canonical write, no repair candidate adopted
