# W16-REV29-CORPUS-REBIND-01 — re-base the two-stage semantic corpus onto FROZEN rev29 and measure acceptance at the frozen bytes

- **worker**: `worker-016` (`worker-16`) — one bounded execution pass
- **class_ids**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **node / gate**: `F1` / `G-FORM`
- **authority**: worker evidence only. This is not a gate verdict, does not set
  `validation_status=passed`, and does not move node status to `done`.
- **budget / spent**: ≤ 3.0 agent-hours declared; ≈ 0.5 h this pass.

## Open item addressed

`B4` of `W069-LIFE05-REC12-REPAIR-COVERAGE-01` (= residual `W16R28-F1`): at FROZEN revision 29 the
frozen acceptance record `artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:7e44de0e3906`
binds `base_sha256 = 1bb78ce9…` while the frozen C0 is `b2ab6acb…`, so
`artifacts/formulation/tools/run_acceptance.py` fails closed in `preflight()` and exits **3**.
No two-stage measurement bound the frozen schemas.

## Bound revision (this pass)

| item | value |
|---|---|
| `artifacts/formulation/FROZEN.json` | `sha256:815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| revision / frozen_at / files | **29** / `2026-09-12T00:57:26+08:00` / **50** |
| `verify_frozen.py` | exit 0 — `50 files, 0 problems` (measured at pass start and pass end) |
| F1 `af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F2a `af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| F2b/C0 `af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| rule spec / corpus manifest | `40f9bb9e657b…` / `c102445df397…` |
| stage tools (unchanged) | structural `000e09e46b2f`, semantic `c79d8ab8440a`, measure `c6e4f9ccce7f`, acceptance `e544c36d2d16` |

**Freeze churn observed (reported, not repaired):** the first attempt at 00:57:01 bound rev29
`3d9e3d77fd87` (48 files); that freeze was replaced 25 s later by rev29 `815e08079aef` (50 files),
and the pass aborted fail-closed, re-snapshotted, and bound the 50-file freeze. The 3 drifted
files of the 48-file freeze (`VARIANT_REGISTRY.json`, both variant deltas) were re-pinned by the
replacement freeze. All numbers below belong to `815e08079aef`; the snapshot was stable through
the pass (`snapshot_drift_at_end = []`).

## Method (no shared/frozen byte touched)

All writes are under `artifacts/worker-16/rev29_rebind/`; reproducible by
`run_rebind_rev29.py`:

1. Reproduce the frozen-bytes failure in an isolated copy of the live tree (exit 3 happens before
   any write); the live frozen evidence hash is re-measured afterwards and is unchanged
   (`shared_evidence_untouched = true`).
2. Build a stage mirror of the frozen input tree; verify every staged input against the snapshot
   pins **and** against `FROZEN.json`'s own recorded hashes (`staged_inputs_all_match = true`,
   `frozen_manifest_crosscheck_all_match = true`).
3. Re-run the sanctioned `measure_semantic_escape.py` in the stage **twice** with the unchanged
   corpus manifest, applied to the frozen C0.
4. Re-run `run_acceptance.py` in the stage (plain for the exit code, `--json` for the body).
5. Capture first-hand raw verdicts of both stages on the three canonical schemas.
6. **Phase B** (`--with-gate-probe`): copy the whole live `artifacts/formulation` tree to two
   byte-identical roots at different absolute paths and run the frozen `run_gate_tests.py` in each,
   to measure `W16R28-F3`.

## Results — phase A (B4)

| quantity | frozen bytes | staged rev29 rebase |
|---|---|---|
| corpus `base_sha256` | `1bb78ce9…` (stale vs C0 `b2ab6acb`) | `b2ab6acb…` = frozen C0 |
| `run_acceptance.py` exit | **3** (PREFLIGHT FAIL) | **1** (FAIL, no longer preflight) |
| rebased evidence | `7e44de0e3906…` (frozen) | `c194a5717a1d47ab…` (14384 B) |
| staged report | `9b7d6c8208d3…` (frozen) | `a4524e61f75d…` (1157 B) |
| mutants | — | 31 (1 manifest mutation unparsable, unchanged) |
| catch | — | structural 30/31, semantic 11/31, **union 31/31**, 0 escapes |
| controls | — | 2/2 pass both stages (not format-dominated) |

- **Rebase is deterministic**: two staged runs produced byte-identical
  `semantic_escape_rebased.json` (`rebased_deterministic = true`).
- **No measurement change**: per-mutant verdicts are identical to the rev28 rebase of the same
  manifest (`55d0a1ea` base) — **0 diffs** over all 31 fixtures; the staged acceptance report is
  byte-identical to the rev28 staged report (`a4524e61f75d`). The rev13 schema repair touched only
  the `f0_binding` metadata field, not any mutated content.
- **Sole residual failure at the frozen bytes:** canonical F1 `af_wcc_vacuum.yaml#d9cebb9404b2`
  passes stage 1 and is rejected by stage 2 with `failed_rules = ['R03']` (first-hand capture in
  `out/raw_verdicts.json`). F2a and F2b pass both stages. This is `W16R28-F2`, already adjudicated by
  `w16-R03-ADJ-01` as a literal-match false positive of the R03 implementation; its disposition
  (Option A amend R03 / Option B change the F1 sentence) remains lead/controller authority.

## Results — phase B (W16R28-F3: location-dependent gate report)

`CONFIRMED`. Two byte-identical copies of `artifacts/formulation` at different absolute roots run
the frozen `run_gate_tests.py` to **different** report bytes but **identical** semantic content:

| probe root | report sha256 | gate verdict | counts |
|---|---|---|---|
| `…/rev29_rebind/probe_a` | `9c63de134ed62adf36fede97641af27da65917aa9af176285a652620ed6237ee` | PASS | 3/3 canonical, 6/6 controls, 31/31 mutants, 2/5 rephrased |
| `…/rev29_rebind/probe_b` | `79e077a819b2091a3aa6eb176fcca06e05b5d7feb06f61c4476cb08e79b3a038` | PASS | 3/3 canonical, 6/6 controls, 31/31 mutants, 2/5 rephrased |

Each report embeds **9 absolute fixture paths**; after replacing each root with `<ROOT>` the parsed
JSON is identical (`normalized_json_identical = true`), and the live frozen
`gate_test_report.json#26540a6b43cc` normalizes to exactly the same object. So the report hash is a
function of the absolute run root: the FROZEN pin is reproducible only from the canonical path, and
any re-run from a different directory changes the hash without changing the gate result. Same
verdict/controls as the rev28 freeze (3/3, 6/6, 31/31, 2/5 rephrased with the 3 pre-existing
blind spots p01/p02/p05).

## Residual open items (not addressed here)

- **Adoption** (lead action): copy `out/semantic_escape_rebased.json` and
  `out/acceptance_pipeline_report.json` onto the frozen evidence paths (or re-run the sanctioned
  tool in place) and bump the FROZEN revision; then `run_acceptance.py` no longer exits 3.
- **W16R28-F2**: canonical F1 stage-2 `R03`; Option A/B lead decision. Until then acceptance exits 1.
- **W16R28-F3**: now measured (above); fix would be to normalize paths before hashing the report,
  or pin the report by a content hash that excludes the run root.
- **W16R28-F4 / freeze churn**: rev29 was re-frozen twice inside 30 s (48 → 50 files); documented above.

## Falsifier

Refute any of: (a) a `run_acceptance.py` exit 0 at the frozen bytes with the current frozen evidence
and unpatched tools (no rebase needed); (b) staged inputs differing from the pinned FROZEN rev29
hashes; (c) two staged `measure_semantic_escape.py` runs yielding different evidence sha256;
(d) the rebased corpus applying a different mutation set than manifest `c102445df397`; (e) a
per-mutant verdict diff between the `1bb78ce9` and `b2ab6acb` corpora; (f) two gate-test reports at
different absolute roots that are byte-identical, or that differ after root normalization (would
refute W16R28-F3 as measured).
