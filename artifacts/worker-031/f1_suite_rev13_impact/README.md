# W031-F1-SUITE-REV13-IMPACT-01 — the rev13 repair left the F1 falsifier suite unbound

**Agent:** worker-031 · **Instance:** `worker-031-20260912T005105-968807`
**Class:** `AF-WCC-VAC-GEN` (cross-refs `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) · **Node:** F1 · **Gate:** G-FORM
**Status:** worker measurement complete; no gate verdict, no node status, no canonical artifact edited.

## Why this task

At 00:53:20 the owner landed `astra-life05-evidence-binding-repair` (controller REC-12): F1
`schemas/af_wcc_vacuum.yaml` rev12 `cce9c60146d6` → rev13 `d9cebb9404b2`, with the same
treatment on F2a/F2b, the corpus rebound at 00:42, and FROZEN re-published as rev29 at
00:54:32–00:55:02. The repair's four authorised items name the corpus, the three
consistency-evidence pins, the F1 strictness text and the manifest. They do **not** name
`schemas/f1_falsifier_tests.jsonl`, the 25-row / 84-probe suite that is G-FORM acceptance
evidence for F1. This instrument measures the impact on that suite at live bytes, and checks
the rev12→rev13 byte delta against the authorised edit surface.

No other worker owns this post-repair suite measurement: `W007-REV29-PREFLIGHT-01` measured the
four repair items pre-repair; `W032-F1AMB25-STALE-VERIFY-01` measured the single F1-AMB-25 F0
staleness; neither measured the row-binding invalidation caused by the rev13 write.

## Result — `SUITE_UNBOUND_AT_F1_REV13`

Live pins at measurement (all decision inputs stable across the run; FROZEN's own hash moved
once more while the repair kept publishing and is reported, not fail-closed):

| input | sha256 |
|---|---|
| suite `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| F1 `schemas/af_wcc_vacuum.yaml` (rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F2a `schemas/af_scc_c2_vacuum.yaml` (rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| F2b `schemas/af_scc_c0_vacuum.yaml` (rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| F0 `research_map/formulation_taxonomy.yaml` (rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| corpus `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` |
| consistency `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| FROZEN (rev29) | `3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833` |

1. **25/25 suite rows are unbound.** Every row carries
   `binding_sha256 = cce9c60146d6…` (the pre-repair F1 rev12 schema) and `binding_ref` to that
   same superseded hash. The live F1 schema is `d9cebb9404b2…`. The superseded token resolves
   to real on-disk snapshots (worker-007/worker-032/worker-060), so this is a stale citation,
   not corrupt data.
2. **The pre-existing F1-AMB-25 F0 staleness survives the repair.** `cross_artifact[0].sha256`
   and the deciding-field expectation still carry F0 `276009f4f63d…`; live F0 is
   `0abb9ed8a961…` (2 of the 27 defects; the other 25 are the row bindings).
3. **Probe recomputation at live rev13: 82/84**, the same 2 failures as at the pre-repair
   snapshot (F1-AMB-25 `f0_binding.declared_f0_sha256` equality and its `binding_note`
   corroborator). The rev13 strictness rewrite itself flipped no probe (`contains` expectations
   such as `TAIL` / `future-inextendible causal geodesic` still hold), so the recompute delta is
   entirely the F0 staleness — but the *binding* delta is a new, total invalidation.
4. **Repair items I1–I4 measured landed at this snapshot:** corpus 36/36 rows bind live F0 rev5
   with no `taxonomy_ref` defect; all three schemas' `f0_binding.consistency_evidence_sha256`
   are live `9e335e9b` (0 schema defects); F1 revision 13 carries the strictness correction; and
   FROZEN rev29 has 48/48 file pins live, 0 stale.
5. **The F1 rev12→rev13 byte delta is inside the authorised edit surface.** 12 flattened paths
   changed, 0 unauthorised, and the class-semantics fields (`class_id`, `hypothesis`,
   `conclusion`, `genericity`, `class_components`, and the variant's identity/statement fields)
   are byte-identical. The 12th path, `quantifiers.domains.D5.definition`, is the second
   location of the same D5 definition and carries the identical authorised strictness
   correction; `class_identity_variants[0].relation` is the authorised direction flip
   (`strictly STRONGER` → `strictly WEAKER`).

## Consequence for G-FORM

G-FORM's F1 evidence suite no longer binds the artifact it is evidence for, and its own
F1-AMB-25 row still asserts a false F0 equality. Until the suite is re-pinned to F1 rev13 +
F0 rev5 and re-run (or explicitly dispositioned as a historical record), the suite's stored
`84/84` claim and its row bindings cannot support a gate verdict, and audit review coverage at
the live F1 hash cannot bind this suite. Minimal repair: rewrite the 25 `binding_sha256` /
`binding_ref` values to `d9cebb9404b2…`, update F1-AMB-25's `cross_artifact` and deciding
expectation to `0abb9ed8a961…`, re-run the author's verifier, and re-publish the suite with an
artifact event + sha256 — then re-run this instrument; it should report `SUITE_STILL_BOUND`
with 25/25 live row bindings and 84/84 probes.

## Method

`check_rev13_impact_031.py` (stdlib + PyYAML, deterministic, offline, fail-closed):

* pins the 8 inputs above by full sha256 and re-measures them at the end; decision-input drift → exit 2;
* resolves every operative `(path, sha256)` pair in the suite (row `binding_sha256`,
  `cross_artifact`, deciding-field hash expectations) against live bytes, and classifies other
  hash tokens (`evidence_refs`, `prior_binding_*`, `binding_at_authoring`) as provenance;
* recomputes all 84 recorded probes against the live F1 rev13 document and against the pinned
  pre-repair rev12 snapshot (`artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml`,
  hash verified before use — exit 2 otherwise);
* censuses the three schemas' `f0_binding` pins, the corpus meta/row pins, and all FROZEN rev29
  file pins vs live bytes;
* diffs the flattened rev12→rev13 YAML against an explicit authorised-path allowlist and checks
  class-semantics invariance.

### Controls (all pass)

| control | result |
|---|---|
| K1 live pin accepted | pass |
| K2 fabricated 64-hex pin rejected as `stale` | pass |
| K3 mutation flips a recorded-pass probe | pass |
| K4 baseline continuity: on the pre-repair snapshot the census reproduces W031-F1-PINCENSUS-01 (25/25 row bindings live, 82/84 recomputed, 2 suite + 3 schema stale pins) | pass |
| K5 replay determinism (two censuses byte-identical) | pass |
| K6 delta-scope sensitivity (synthetic `class_id` mutation flagged unauthorised) | pass |
| K7 class semantics unchanged across rev13 (relation/note excluded as the authorised edit) | pass |

Exit code 0 = measured; 1 = control failure; 2 = decision-input drift or snapshot hash mismatch.

## Prior-reporting crosswalk (non-duplication)

* `W031-F1-PINCENSUS-01` (worker-031, 00:42, `artifacts/worker-031/f1_pin_census/`) — the
  5-stale-pin pre-repair baseline reproduced here by control K4.
* `W032-F1AMB25-STALE-VERIFY-01` (worker-032, 00:42, `artifacts/worker-032/f1amb25/`) — the
  F1-AMB-25 F0 staleness; confirmed here, not claimed as new.
* `W007-REV29-PREFLIGHT-01` (worker-007, 00:52, `artifacts/worker-007/rev29_preflight/`) —
  repair items I1–I4 pre-repair; this report measures them post-repair.
* `W076-GFORM-STRICTNESS-RECONCILE-06` (worker-076, 00:51) — diagnosed the strictness direction
  defects that rev13 corrects; the authorised-delta scope check here confirms the correction
  changed no class semantics.
* New in this report: the 25/25 row-binding invalidation of the F1 suite caused by the rev13
  schema write, and the post-repair status of I1–I4 at one pinned snapshot.

## Falsifier

This report is void if any pinned decision input (suite, F1/F2a/F2b, F0, corpus, consistency
evidence) moved during the run (`inputs_stable_during_run` false), if any of K1–K7 fails, if a
flagged `stale` pair is shown to be provenance rather than an operative binding, or if the suite
has been re-pinned to the live F1/F0 hashes and re-published before this verdict is read — the
last repairs the finding rather than falsifying it.

## Next falsifier

After the suite is re-pinned and re-published: re-run this instrument at the new pins. Expected
`SUITE_STILL_BOUND`, 25/25 row bindings live, 84/84 probes reproducing at the then-live F1/F0
pair. If only FROZEN is re-pinned and the suite stays at `56bcb4b3234b`, the suite remains
evidence-stale and G-FORM cannot bind it.

## Authority

Worker measurement only: no `status=done`, no `validation_status=passed`, no gate verdict, no
node status, no artifact under test edited. Repair ownership stays with the formulation lead;
the G-FORM verdict stays with the controller/audit lead.

## Replay

```bash
cd <swarm-root>
python3 artifacts/worker-031/f1_suite_rev13_impact/check_rev13_impact_031.py   # exit 0, rewrites report.json
```
