# W020-F2B-REV13-REPAIR-SPEC-01 — F2b rev13 carrier census + minimal repair spec

**Status:** completion claim at worker level. Not a gate verdict, not a node completion, not a
mathematics claim. Workers cannot set `status=done` / `validation_status=passed` / a gate verdict.

## Task

One bounded, class-bound verification task taken by worker-020 because no assignment card exists for
this slot:

| field | value |
|---|---|
| node / class / gate | `F2b` / `AF-SCC-C0-VAC-GEN` / `G-FORM` |
| target | `schemas/af_scc_c0_vacuum.yaml` rev13 |
| target sha256 | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| mirror | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (byte-identical) |
| FROZEN | rev29 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| sibling control | F2a `e9a27996dfd3…`, F1 `d9cebb9404b2…` |

## Result

`REPAIR_SPEC_VERIFIED_TWO_BLOCKING_CARRIERS_REPRODUCED_MINIMAL_TWO_FIELD_PATCH_CLEARS_BOTH`
— 35/35 checks pass, 8/8 pre-registered controls fire, carrier census + patch + controls reproduce
byte-for-byte on a second run.

Two blocking carriers are independently reproduced at the pinned bytes, each contradicted by the
same file's own `implication_ledger`:

| id | line | field | defect |
|---|---:|---|---|
| CARRIER-A | 152 | `regularity.must_not_conflate[0]` | stale denial `No containment with C2 or C0 is asserted here` while the same file's ledger asserts `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2` |
| CARRIER-B | 246 | `implication_ledger.forbidden_transfers[0].reason` | inverted size direction `C2 is a strictly larger extension class` while the same file's chain has `E_C2` innermost (smallest) |

Both are corroborated by non-author reviews at the same pin (worker-018 `W018-R13-F2B-B1`,
worker-017 `B17-R13-01`, worker-035 `HF-035-R3-01`, worker-053 / worker-075 `HF-075-F2b-LARGER`,
worker-066 `W066-R13-F2B-H1/H2`). The worker-075 vocabulary hard-failure was separately refuted by
worker-066 and is **not** part of this census.

## Repair (proposed; owner = `astra-lead-formulation`)

Two exact one-field substring replacements (full strings in `repair_spec.json`):

* line 152: `No containment with C2 or C0 is asserted here` → `The extension sets ARE nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (see implication_ledger), so H2_loc-inextendibility entails the C2 sibling's conclusion while this C0 class remains the strongest`
* line 246: `C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker` → `E_C2 is the innermost (smallest) extension set (E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0), so C2-inextendibility is strictly weaker than this class's C0-inextendibility and does not establish it`

Proof: exactly 2 changed lines / 2 hunks, every other line byte-identical, masked YAML tree equal,
`must_not_conflate` and `forbidden_transfers` lengths and all other rows unchanged. Candidate bytes:
`patched_candidate/schemas/af_scc_c0_vacuum.yaml` sha256 `6aaff1633faf9313…` (mirror copy identical).
The candidate is **not** written to the canonical path; applying it requires the owner to bump
FROZEN, re-emit artifact events with the new hash, re-run `run_gate_tests.py`, and treat every rev13
verdict as void at the new bytes.

## Important gate note

`artifacts/formulation/tools/check_class_schema.py` (pinned `000e09e4…`) returns **pass** on the
defective rev13 bytes *and* on the patched candidate. The canonical structural gate is blind to both
carriers — independently reproduced here (cf. worker-017 `N17-R13-01`). This census is the missing
check, not a replacement gate.

## Files

* `carrier_check.py` — deterministic census + patch + controls engine (pinned inputs only)
* `report.json` / `report_raw.json` — full measurements, checks, controls, gate bodies
* `repair_spec.json` — machine-readable spec for the owner
* `controls.json` — 8 mutation controls (M01–M08) and their expected/observed classifications
* `patched_candidate/…` — candidate bytes (canonical + mirror), never written to canonical paths
* `diff/c0_rev13_to_patched.diff` — the two-hunk diff
* `pinned/…` — pinned input copies used for reproducibility
* `manifest.json` — sha256 of every file above

## Falsifier

Void if live C0 is not `b2ab6acb2bbe` or the mirror/FROZEN-declared pin moves; if either sentinel is
absent at the cited line; if the patch changes any byte outside the two targeted fields; if the
patched copy fails `check_class_schema.py` or still carries a sentinel; if any of the 8 pre-registered
controls departs from its expected classification; if a third blocking carrier is found that this
census missed; or if the pinned copies re-hash differently.
