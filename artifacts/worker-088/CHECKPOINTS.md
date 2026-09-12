# worker-088 checkpoints — F2a frozen-revision review

Task (class-bound): node `F2a`, class `AF-SCC-C2-VAC-GEN`, gate `G-FORM`.
One bounded task, then exit. No gate/status promotion is claimed (worker authority limit).

| # | wall clock (+08:00) | action | artifact / hash | state |
|---|---|---|---|---|
| 0 | 00:17 | read `HANDOFF.md`, `research_map/ASTRA_HANDOFF.md`, `comms/PROTOCOL.md`, `research_map/research_map.json`, latest lifecycle `lifecycle_20260912-001727.json`; selected the unclaimed F2a review at the frozen canonical revision (F1/F2b/F1-review work already claimed by workers 03/06/16/059) | — | task claimed |
| 1 | 00:19:14 | pinned `schemas/af_scc_c2_vacuum.yaml` rev11 | snapshot `artifacts/worker-088/f2a_review/pinned/af_scc_c2_vacuum.b6123750.yaml` = `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` | pinned |
| 2 | 00:20:20–00:20:40 | stability probe (3 × 10 s): canonical F2a and F0 hashes unchanged | F2a `b6123750b37d…`, F0 `276009f4f63d…` | stable |
| 3 | 00:22:0x | wrote and ran deterministic probe `check_f2a.py` (field matrix, binder resolution, D0 disjunction probe, class-token scan, inflation probe, f0-binding resolution, cross-schema compare, frozen class-separation detector, frozen binding gate) | `check_f2a.py` = `6d5d2f7923c3208c724beee1454b94fc3cc843d21dfcc4762b84ce4dd97c858d`; `f2a_check.json` = `cedc8a47d4f6fae3daa63e6e34e17aa816ec9d289bae7fdd6418bb7203364aea` | probed |
| 4 | 00:22:55 | issued review at the frozen hash | `reviews/F2a-review-088.json` = `95bc0c65f88ee1b147104c90c5e1ccc5ebaffff0f0c3a4dae23d3e7f3bac6f35` | emitted |
| 5 | 00:2x | emitted events to `comms/outbox/worker-088.jsonl`; validated with `comms.py ingest --dry-run`; re-hashed F2a for drift | see outbox | checkpointed |

## Result

- verdict: **revise**, score 3.0 (reviewer `worker-088`, not the author).
- hard failure `HF-088-1`: `quantifiers.domains.D0` is a disjunction (Sobolev pairs **or** the
  smooth-with-decay default); the formal binder `(s,delta)` has no instantiation for the smooth
  branch and `genericity.ambient_space` defines an ambient object only for the weighted Sobolev
  product. The formal sentence therefore has an uninstantiable disjunct and the artifact is a
  family of two class statements, not one. Lines 47, 52, 58, 137–138, 163–164, 218.
- major `F-088-1`: duplicate YAML key `revised_at` ×8 (lines 8–23) → parser-dependent revision
  metadata; not a hard failure under the A0 taxonomy, but blocks "machine-frozen".
- major `F-088-2`: F1 vs F2a/F2b data-class mismatch (`excluded_data` key; differing
  `regularity_class` text) — cross-artifact, fix owned by lead-formulation.
- positives: 26/26 acceptance fields, all binder domains resolve, `extension_predicate` now
  defined (prior dangling-core HF fixed), frozen binding gate `PASS`, class-separation detector
  `[]` with regression 17/17 + 10/10, no class leakage, no WCC inflation, `f0_binding` resolves
  to measured F0 `276009f4f63d`, decidable two-tier falsifier.

## Falsifier / next check

Re-run `check_f2a.py` at the next F2a revision. Accept only if
`d0_ill_typed_for_smooth_branch == false` **and** F1/F2b share the same frozen
`regularity_class` **and** the binding gate still passes and the class-separation detector is
still clean. If D0 is only reworded without a smooth-branch ambient space (or without collapsing
D0 to one parameterised class), `HF-088-1` stands.

## Drift

`sha256_before_read == sha256_after_read == b6123750b37d…` (`drifted_during_read=false`).
If the canonical file changes, this review is superseded and must be re-issued at the new hash.

```json
{"checkpoint": "w088-ckpt-1", "at": "2026-09-12T00:25:00+08:00", "actor": "worker-088",
 "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
 "artifact_sha256": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
 "review": "reviews/F2a-review-088.json#95bc0c65f88e", "verdict": "revise", "score": 3.0,
 "hard_failures": ["HF-088-1"], "state": "emitted", "next_falsifier":
 "re-run check_f2a.py at the next revision; accept only if d0_ill_typed_for_smooth_branch=false and the three G-FORM data classes match"}
```

---

# worker-088 checkpoints — F1 hash-bound finding verification (second task)

Task (class-bound): node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`. One bounded task,
then exit. No gate/status promotion is claimed (worker authority limit).

| # | wall clock (+08:00) | action | artifact / hash | state |
|---|---|---|---|---|
| 0 | 00:30:08 | claimed the task from the standing G-FORM requirement + ASTRA_HANDOFF pass-03 open F1 findings; no worker-088 inbox assignment existed | claim event `w088-20260912T0030-task-claim-f1` | claimed |
| 1 | 00:30:55 | pinned and probed rev11 `9a8bd4c9` with `check_f1.py` v1 | `check_f1.py` = `9459bac7c6de…` (v1); report = `fb106692c10b…` | probed |
| 2 | 00:32 | diffed bytes: rev11 confirms all four open findings (tail clause uses whole geodesic; `AF_{I+}` undefined; `revised_at` ×7 + `revised_at_unused` ×2 with declared `00:30:00` vs mtime `00:19:14`; pointer into the divergent authoring taxonomy, canonical has no `class_contracts`) | pinned copy `af_wcc_vacuum.9a8bd4c9.yaml` = `9a8bd4c9…` | confirmed |
| 3 | 00:33:06 | emitted rev11 verdict: revise, score 2.5, HF-088-F1-1 critical + HF-088-F1-2…5 major, blocker for lead-formulation | `reviews/F1-review-088.json` = `916d1ca76fe3…` | emitted |
| 4 | 00:32:02–00:37 | **moving target:** canonical F1 published rev12 `cce9c601` during emit (astra-life03-close-findings); re-pinned and made the probe revision-fair (tail-slice detector, definition-leaf finder, tagged-union D0 detector, dotted anchor resolution, strict+normalized cross-schema compare); regression-checked v2 on rev11 (still flags all four) | `check_f1.py` = `d9d87b1f1717…` (v2); `af_wcc_vacuum.cce9c601.yaml` = `cce9c601…` | re-pinned |
| 5 | 00:37 | re-probed rev12: duplicates `[]`, tail predicate matches, `AF_{I+}` defined at `$.i_plus.predicate_abbreviation`, pointer canonical with anchor resolving, D0 tagged union well-typed, gate PASS, classsep clean, `f0_binding` resolves to new canonical F0; strict `data_class` still not byte-identical across F1/F2a/F2b | `f1_check.rev12.json` = `0cb9a8825a6d…` | probed |
| 6 | 00:37:35 | emitted superseding verdict at rev12 and checkpoint; rev11 review/blocker marked superseded for the new bytes | `reviews/F1-review-088-rev12.json` = `c41daebeba77…`; review event `w088-20260912T003735-review-f1-rev12` | emitted |

## Result at rev12 (`cce9c601`)

- verdict: **accept**, score 4.0, zero hard failures (reviewer `worker-088`, not the author).
- all four rev11 findings mechanically fixed: (1) formal visibility clause is now the declared
  single-q tail predicate `not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q)`;
  (2) `AF_{I+}` has a definition leaf `i_plus.predicate_abbreviation` and
  `undefined_symbols_in_statement_formal=[]`; (3) `yaml_duplicate_keys=[]`, single `revised_at`
  `00:31:41` with `revision_history`, before the file mtime `00:32:02`; (4) `class_contract_pointer`
  → `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN` resolves in the canonical
  taxonomy, supplement split into `class_contract_supplement_pointer`.
- `d0_ill_typed_for_smooth_branch=false`: D0 is a tagged disjoint union over index `r` with
  per-branch ambient spaces; all binders resolve; binding gate `PASS`; class-separation `[]` and
  regression 17/17 + 10/10 PASS; `f0_binding` resolves to canonical F0 `0abb9ed8a961`.
- remaining, non-blocking for F1-local conformance: `F-088-F1-9` (major, cross-artifact,
  adjudication required) strict `data_class` blocks differ (F1-only `excluded_data`; `adm_mass`
  field sets; prose) although D0 is byte-identical and the numeric `(s,delta,norm)` contract is
  equal; `F-088-F1-10` (minor) `P_WCC` still undefined in `negation_normal_form`.

## Falsifier / next check

Accept binds `cce9c601` only. Re-run `check_f1.py` if F1 moves; the accept is falsified by
`formal_matches_declared_predicate=false`, non-empty `undefined_symbols_in_statement_formal`,
duplicate/forward-dated revision keys, a non-canonical or non-resolving `class_contract_pointer`,
`d0_ill_typed_for_smooth_branch=true`, or a failing binding gate / non-clean class separation.
`F-088-F1-9` clears on byte-identical `data_class` blocks or an explicit gate-owner ruling that
the shared `(s,delta,norm)` contract satisfies the G-FORM criterion at one hash.

## Drift

rev11: `9a8bd4c9…` stable across read/parse/probes. rev12: `cce9c601…` stable across
read/parse/probes and still canonical at emit (`00:37:35`). If either file changed after its
verdict, the corresponding review is superseded and must be re-issued at the new hash.

```json
{"checkpoint": "w088-ckpt-3", "at": "2026-09-12T00:37:35+08:00", "actor": "worker-088",
 "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
 "artifact_sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
 "review": "reviews/F1-review-088-rev12.json#c41daebeba77", "verdict": "accept", "score": 4.0,
 "hard_failures": [], "supersedes": "reviews/F1-review-088.json#916d1ca76fe3 (revise at 9a8bd4c9)",
 "state": "emitted", "moving_target": "rev11 -> rev12 during emit; both verdicts are hash-bound",
 "next_falsifier": "re-run check_f1.py if F1 moves; F-088-F1-9 clears on byte-identical data_class blocks or a gate-owner ruling on the shared (s,delta,norm) contract"}
```

## Correction (ckpt-4, 00:39) — the rev12 accept is withdrawn

At 00:36:58 worker-078 issued an independent revise at the *same* hash `cce9c601` citing a
binding-hygiene defect not covered by probe v2: `f0_binding.consistency_evidence_sha256 =
675a99d0d25b` no longer resolves because `artifacts/formulation/evidence/taxonomy_consistency.json`
was regenerated at 00:38:07 (measured `9e335e9ba1bf`), after the binding's `checked_at`
00:31:41 — and F1's own `f0_binding.rule` forbids a gate verdict until the check is re-run and
the binding refreshed. Probe v3 (`fd98d79a78f2…`) adds that check and re-derives the defect from
the bytes; the accept at `cce9c601` is withdrawn and replaced by **revise, score 3.5,
HF-088-F1-12**. The withdrawn accept file is left on disk with its hash; the correction is a new
review (`reviews/F1-review-088-rev12-amended.json` = `f49f1c2c4f5a…`), not a rewrite. All rev12
semantic/structural repairs remain verified; `F-088-F1-9` (strict cross-schema `data_class`
identity) and `F-088-F1-10` (`P_WCC` undefined in the NNF) remain as recorded above.

```json
{"checkpoint": "w088-ckpt-4", "at": "2026-09-12T00:39:02+08:00", "actor": "worker-088",
 "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
 "artifact_sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
 "review": "reviews/F1-review-088-rev12-amended.json#f49f1c2c4f5a", "verdict": "revise", "score": 3.5,
 "hard_failures": ["HF-088-F1-12 (stale consistency-evidence hash)"],
 "supersedes": "reviews/F1-review-088-rev12.json#c41daebeba77 (accept withdrawn at the same hash)",
 "state": "emitted", "probe": "check_f1.py#fd98d79a78f2 (v3, adds consistency-evidence resolution)",
 "next_falsifier": "accept at one hash only after consistency_evidence_resolves=true and F-088-F1-9 is adjudicated; re-run check_f1.py v3 if F1 moves"}
```

---

# worker-088 checkpoints — F2a rev12 re-verification (third task)

Task (class-bound): node `F2a`, class `AF-SCC-C2-VAC-GEN`, gate `G-FORM`. One bounded task,
then exit. No gate/status promotion is claimed (worker authority limit). No worker-088 inbox
assignment existed; the task is this worker's own recorded next_falsifier (ckpt-1/ckpt-2):
re-run the F2a probe at the next revision, accept only if `d0_ill_typed_for_smooth_branch=false`
and the three G-FORM data classes match. F2a moved rev11 `b6123750` → rev12 `5476a3f2`
(FROZEN r28), so the rev11 verdict is superseded.

| # | wall clock (+08:00) | action | artifact / hash | state |
|---|---|---|---|---|
| 0 | 00:41 | read `HANDOFF.md`, `research_map/ASTRA_HANDOFF.md` (pass-04), `comms/PROTOCOL.md`, map gates/assignments/reviews, own outbox; selected the unclaimed F2a rev12 re-verification from the standing G-FORM requirement and the recorded next_falsifier | — | task claimed |
| 1 | 00:42 | pinned rev12 `5476a3f2` and measured siblings: F1 `cce9c601`, F2b `55d0a1ea9bda`, F0 `0abb9ed8a961`, evidence `9e335e9ba1bf`, tool `000e09e4`, manifest `014e2d30`, FROZEN r28 `2f358f6722d9` | snapshot `artifacts/worker-088/f2a_review/pinned/af_scc_c2_vacuum.5476a3f2.yaml` = `5476a3f2…` | pinned |
| 2 | 00:43–00:44 | wrote and ran revision-fair probe `check_f2a_v2.py` (D0 tagged-union well-typedness, 26-field matrix, binder resolution, pointer resolution in both taxonomies, F0 + consistency-evidence hash resolution with mtime ordering, conclusion-vocabulary check vs F0 allowed list and VOCAB_ALIASES, canonical binding gate with tool+manifest hashes, class-separation detector, cross-schema compare, FROZEN pin, drift) | `check_f2a_v2.py` = `6dda0da3da16…`; `f2a_check.rev12.v2.json` = `ae042fd655f9…` | probed |
| 3 | 00:45 | issued rev12 verdict: revise 3.5, HF-088-F2a-CE + HF-088-F2a-VOC, three majors; HF-088-1 verified repaired | `reviews/F2a-review-088-rev12.json` = `a801d2104c9c…` | emitted |
| 4 | 00:46 | appended `review` + `status` events to `comms/outbox/worker-088.jsonl`; `comms.py ingest --dry-run`: accepted 2, rejected 0 | outbox | checkpointed |

## Result at rev12 (`5476a3f2`)

- verdict: **revise**, score 3.5, reviewer `worker-088` (not the author).
- **closed:** `HF-088-1` (rev11 D0 disjunction ill-typed for the smooth-with-decay branch).
  D0 is now a tagged disjoint union over `r` (`r = smooth` | `r = (sobolev,s,delta)`) with a
  per-branch ambient space, the formal statement is `forall r in D0`, the ordered binder is `r`,
  and both legacy markers are absent (`d0_ill_typed_for_smooth_branch=false`,
  `hf088_1_repaired=true`). Placeholder-only checks would not have caught the repair; the
  detector tests the typed-union contract, not the phrase "tagged union".
- **hard `HF-088-F2a-CE`:** `f0_binding.consistency_evidence_sha256 = 675a99d0` does not resolve;
  measured evidence is `9e335e9ba1bf` (stable hash, mtime advances) and was regenerated after
  `checked_at` 00:31:41. Same defect class as `HF-088-F1-12`. New probe gap closed: the evidence
  document records no compared-input hashes, so re-stamping alone cannot clear it.
- **hard `HF-088-F2a-VOC`:** `conclusion_type = scc_c2_future_inextendibility` is not in the bound
  F0 `field_vocabulary.conclusion_type.allowed`; independently `VOCAB_ALIASES.json` (`46cd9f1e`)
  declares it a canonical key and `strong_cosmic_censorship_C2` an alias that must not appear in a
  new canonical artifact. Registry-governance conflict; gate-owner adjudication required.
- **majors:** `F-088-F2a-M1` F1 `data_class.regularity_class` still differs (cross-artifact,
  although D0 is byte-identical across all three); `F-088-F2a-M2` the worker-005/096 R22 failure
  does **not** reproduce against measured manifest `014e2d301978` (gate PASS, `failed_rules=[]`) —
  gate verdict is manifest-dependent and should pin the manifest hash; `F-088-F2a-M3` embedded
  `review_status` is stale (`independent_reviewers=[]`, `verdict=pending`) against ≥6 reviews at
  this hash.
- passes: 26/26 required fields, `yaml_duplicate_keys=[]`, all binder domains resolve, canonical
  pointer resolves under `research_map/formulation_taxonomy.yaml#classes`, supplement pointer
  resolves under `#class_contracts`, F0 declared hash resolves, gate PASS at tool `000e09e4` /
  manifest `014e2d30`, class-separation `[]`, no unknown class tokens, no WCC/C0 inflation,
  FROZEN r28 pin matches the measured bytes.

## Falsifier / next check

Accept binds `5476a3f2` only if, at one frozen hash: `consistency_evidence_resolves=true` after a
re-run whose evidence document records the compared input sha256s; the conclusion-type token is in
the bound F0 vocabulary or a recorded gate-owner ruling designates the alias registry canonical;
`d0_ill_typed_for_smooth_branch` stays false; the binding gate PASSes with tool+manifest hashes
recorded; class separation stays clean; and `F-088-F2a-M1` is adjudicated or the three
`data_class` blocks are byte-identical.

## Drift

`sha256_before_read == sha256_after_probe == 5476a3f2…` (`drifted_during_probe=false`);
`taxonomy_consistency.json` is rewritten with identical content (`9e335e9b…` stable across the
probe) while its mtime advances. If the canonical F2a file moves, this review is superseded and
must be re-issued at the new hash.

```json
{"checkpoint": "w088-ckpt-5", "at": "2026-09-12T00:46:30+08:00", "actor": "worker-088",
 "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
 "artifact_sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
 "review": "reviews/F2a-review-088-rev12.json#a801d2104c9c", "verdict": "revise", "score": 3.5,
 "hard_failures": ["HF-088-F2a-CE (stale consistency-evidence hash; evidence not hash-bound)",
                   "HF-088-F2a-VOC (conclusion-type registry conflict, needs gate-owner ruling)"],
 "closed_hard_failures": ["HF-088-1 (rev11 D0 disjunction ill-typed; repaired at rev12)"],
 "state": "emitted", "probe": "check_f2a_v2.py#6dda0da3da16",
 "frozen_pin": "artifacts/formulation/FROZEN.json#2f358f6722d9 rev28 pin matches",
 "next_falsifier": "re-run check_f2a_v2.py at the next revision; accept only on consistency_evidence_resolves=true (evidence recording input hashes), adjudicated conclusion-type registry, gate PASS with tool+manifest hashes, and F-088-F2a-M1 adjudicated"}
```
