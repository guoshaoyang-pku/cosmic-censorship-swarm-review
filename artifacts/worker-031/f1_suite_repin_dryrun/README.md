# W031-F1-SUITE-REPIN-PROPOSAL-01 — dry-run re-pin of the F1 falsifier suite

**Agent** worker-031 · **class** `AF-WCC-VAC-GEN` (refs `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) ·
**node** F1 · **gate** G-FORM · **verdict** `PATCH_VALIDATED_AT_LIVE_PINS` · worker measurement only.

The owner's blocker `L-FORM-04` (astra-lead-formulation, 2026-09-12T00:57:43+08:00) declares
`56bcb4b3234b` NOT re-bound to F1 rev13 `d9cebb9404b2`. worker-029 and
worker-032 measured that defect; this task builds the **repair as an exact patch**, applies it to
artifact-local copies only, and measures that it closes every defect at the live pins.

## Question

What is the minimal patch to `schemas/f1_falsifier_tests.jsonl` that makes the suite self-consistent
at F1 rev13 / F0 rev5 / FROZEN rev29, and what does that patch cascade into?

## Pins (full sha256; drift-guarded before and after the run)

| path | sha256 | role |
|---|---|---|
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` | suite under repair (read-only) |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` | F1 rev13 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | F0 rev5 |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` | rev29 |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` | corpus |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` | consistency |
| `artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` | pre-repair rev12 snapshot |

All 10 pinned inputs matched at start and finish (`inputs_stable_during_run: True`).

## Result

| measurement | baseline (canonical) | tier A (operative only) | tier B (recommended) |
|---|---:|---:|---:|
| row bindings live | 0/25 | 25/25 | 25/25 |
| `binding_ref` vs `binding_sha256` consistent | 25/25 | 25/25 | 25/25 |
| cross-artifact live | 0/1 | 1/1 | 1/1 |
| stored probes re-evaluating true | 82/84 | 84/84 | 84/84 |
| vendor C1a/C1b/C2/C4–C10 | 5/10 pass | 10/10 pass | 10/10 pass |
| JSON-pointer changes | — | 53 | 84 |
| patched sha256 | — | `e172020ccda52b605a06cb0d41e67d36e8854d326c3e92dda33c023339831dae` | `785e6a4e53d6437796fbe40a09ed391d54ec1c8264f3d338a93f5bd9f00c9b4a` |
| patched bytes | 145895 | 145971 | 146501 |

Baseline defect set (exactly as pre-registered): 25/25 row bindings stale (all carry pre-repair F1
`cce9c60146d6`), the single `F1-AMB-25` cross-artifact binding stale (F0 rev4 `276009f4`), and the two
`F1-AMB-25` stored probes false — probe 0 `f0_binding.declared_f0_sha256` (expects `276009f4`) and
probe 3 `f0_binding.binding_note` (expects `astra-classscope-02`). The same two probe mismatches
recompute at the hash-verified pre-repair rev12 snapshot, so the rev13 staging did not introduce them.

**Tier A** (53 pointers): 25× `binding_ref`+`binding_sha256` → rev13; `F1-AMB-25`
`cross_artifact[0].sha256` and probe 0 `expected` → live F0 `0abb9ed8`; probe 3 `expected` →
`V1` anchor.
**Tier B** (84 pointers, recommended): tier A plus provenance/descriptive refresh —
`binding_frozen_revision` → 29 on all rows, `binding_frozen_revision_schema` → 13, `rebound_at`
(placeholder), `rebind_note`, both `observed_excerpt`s, and the F0 `evidence_refs` entry.

Minimality: the measured changed-pointer set equals the declared set exactly on both tiers
(0 unexpected, 0 declared-but-inert, row set unchanged). Semantics: the full question/deciding-field/
falsifier/class key set is identical on all 25 rows on both tiers.

## Cascade (not a worker action)

FROZEN rev29 pins `schemas/f1_falsifier_tests.jsonl` at `56bcb4b3234b`;
any re-pin moves that one path, so `change_protocol` requires **FROZEN rev30** with the new
sha256/bytes, a re-emitted artifact event, a refreshed `runtime/state/artifact_hashes.json`, and a
vendor-verifier re-run. F1/F2a/F2b/F0 bytes and their FROZEN pins are untouched.

## Owner decisions

- binding_note anchor variant: V1 (current rev13 operative text, primary) vs V2 (F0-contract anchor); both measured 84/84
- rebound_at/rebind_note actual values: the dry-run uses a declared placeholder instant; owner sets the re-publish instant
- tier A vs tier B: tier A is the minimal operative repair (53 pointers, hash e172020ccda5); tier B also refreshes provenance/descriptive fields (84 pointers, hash 785e6a4e53d6) and is the recommended published form
- FROZEN rev30 bump + artifact event + registry refresh + vendor verifier re-run are outside worker authority

## Controls (10/10 pass)

| control | value |
|---|---|
| K1 serializer round-trip byte-identical | `True` |
| K2 revision-responsive decoy (sandbox F1 rev14) | 25/25 stale |
| K3 `binding_sha256` operative | 25/25 stale, 25/25 ref-inconsistent |
| K4a drop deciding `expected` | 83/84 (mismatch [0]) |
| K4b drop `binding_note` `expected` | 83/84 (mismatch [3]) |
| K5 cross-artifact operative | 1 stale, probes 84/84 |
| K6 anchor variants | V1=84/84, V2=84/84 |
| K7 input drift at finish | stable `True` |
| K8 patch determinism (fresh loads) | `True` |
| K9 sandbox confinement | canonical paths written: [] |

## Deliverables

| path | sha256 (computed at emit) |
|---|---|
| `report.json` | 61aed017c233b65e628acaeed7e4e76203b45b5cc9384b2552193177aeb6e89a |
| `PROPOSED_PATCH.json` | b3288de1c30a28c798202e82f132d2b7b16ec1e609c284285c4569a804a0900a |
| `dryrun_repin_031.py` | 7f958bd140cb7cd363a600a523b51032af037ba3aba1eb68ba890e5c170ab8f8 |
| `patched/f1_falsifier_tests.tierA.jsonl` | e172020ccda52b605a06cb0d41e67d36e8854d326c3e92dda33c023339831dae |
| `patched/f1_falsifier_tests.tierB.jsonl` | 785e6a4e53d6437796fbe40a09ed391d54ec1c8264f3d338a93f5bd9f00c9b4a |
| `CHECKPOINT.json` | 0db4c7629bbb9881630dc34a99835149291598807fa182aeb08d7e54262da573 |

**Falsifier.** Any pinned decision input moving during the run; a declared pointer whose application does not change the measured semantics; a tier whose patched suite does not reach 25/25 live bindings + 1/1 live cross-artifact + 84/84 probes + all vendor C-checks; or an owner-applied re-pin whose bytes differ from the proposed bytes without a recorded reason.

**Next falsifier.** Owner applies the re-pin and bumps FROZEN to rev30; then re-run this instrument with the suite pin replaced by the published bytes and EXPECT 0 outstanding defects and PATCH-ALREADY-APPLIED (round-trip: proposed bytes == published bytes). If the published bytes differ, diff the pointer sets before accepting.

**Authority.** Worker measurement only. No canonical path was written: the patch exists solely as
`PROPOSED_PATCH.json` + the two artifact-local `patched/*.jsonl` files. No gate verdict, no node
status, no `validation_status`.

**Replay.** `python3 artifacts/worker-031/f1_suite_repin_dryrun/dryrun_repin_031.py`
