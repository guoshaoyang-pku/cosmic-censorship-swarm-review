# W16-CORPUS-REBIND-01 — re-base the semantic corpus onto FROZEN rev28 C0 (stage-side resolution of W16R28-F1)

- **worker**: worker-016 (`worker-16`) — bounded execution pass
- **class_ids**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **node / gate**: `F1` / `G-FORM`
- **authority**: worker evidence only. This is not a gate verdict, does not set
  `validation_status=passed`, and does not move node status to `done`.
- **budget / spent**: ≤ 3.0 agent-hours declared; ≈ 0.6 h this pass.

## Open item addressed

`W16R28-F1` (from review `w16-REV28-VERIFY-01-review-acceptance`): the frozen
`artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:7e44de0e3906`
binds `base_sha256 = 1bb78ce9…` (a superseded C0 revision), while the frozen C0 is
`55d0a1ea…`. `artifacts/formulation/tools/run_acceptance.py` therefore fails closed in
`preflight()` and exits **3** at frozen bytes — the acceptance evidence cannot bind the
current frozen schemas.

## Method (no frozen byte touched)

All writes are under `artifacts/worker-16/corpus_rebind/`. Steps, all reproducible by
`run_rebind.py`:

1. Reproduce the frozen-bytes failure **read-only** (exit 3 happens before any write).
2. Build an isolated stage mirror of the minimal frozen input tree and verify every
   staged input sha256 against the pinned identities **and** against `FROZEN.json`'s own
   recorded hashes (`staged_inputs_all_match = true`, `frozen_manifest_crosscheck_all_match = true`).
3. Re-run the sanctioned tool `measure_semantic_escape.py` in the stage, **twice**, with
   the unchanged corpus manifest `c102445df397` applied to the frozen C0.
4. Re-run `run_acceptance.py` in the stage (plain for the exit code, `--json` for the body).
5. Capture first-hand raw verdicts of both stages on the three frozen canonical schemas.

## Results

| quantity | before (frozen bytes) | after (stage rebase) |
|---|---|---|
| corpus `base_sha256` | `1bb78ce9b357…` (stale) | `55d0a1ea9bda…` = current frozen C0 |
| `run_acceptance.py` exit | **3** (PREFLIGHT FAIL) | **1** (FAIL, no longer preflight) |
| rebased evidence sha256 | `7e44de0e3906…` (frozen) | `c14077ab9a82…` (new, 14384 bytes) |
| staged report sha256 | `9b7d6c8208d3…` (frozen) | `a4524e61f75d…` (new, 1157 bytes) |
| gate / stage-2 tool | `000e09e46b2f` / `c79d8ab8440a` | unchanged (`000e09e46b2f` / `c79d8ab8440a`) |
| corpus manifest | `c102445df397` | unchanged (`c102445df397`) |

**Rebase is deterministic**: two independent staged runs produced byte-identical
`semantic_escape_rebased.json` (`rebased_deterministic = true`).

**Measurement (stage, frozen C0):** 31 rebased mutants (1 manifest mutation unparsable,
unchanged), structural caught 30/31, stage-2 semantic caught 11/31, **union caught
31/31**, 0 escapes, 2/2 controls pass both stages → not format-dominated.

**Per-mutant verdicts are identical to the pre-rebase corpus** (`verdict diffs = []`):
the superseded C0 revision did not touch any mutated field. The stale-base alarm was a
*binding/hygiene* failure, not a measurement change — but it still hard-fails the
pipeline, and the frozen evidence cannot be cited against the frozen schemas.

**After rebase the pipeline still exits 1, for exactly one reason:** canonical
`af_wcc_vacuum.yaml` passes stage 1 but is rejected by stage 2 with
`failed_rules = ['R03']` (first-hand capture in `out/raw_verdicts.json`). F2a and F2b
pass both stages. That is `W16R28-F2` — already adjudicated by `w16-R03-ADJ-01` as a
literal-match false positive of the R03 implementation, with disposition
Option A (amend R03; no frozen byte change) vs Option B (one-clause F1 change + new hash
+ re-review) reserved to the lead/controller. **The corpus rebase is therefore necessary
but not sufficient for `run_acceptance.py` exit 0.**

## Adoption (lead action; frozen paths intentionally unmodified here)

Either copy the staged bytes onto the frozen paths:

```
cp artifacts/worker-16/corpus_rebind/out/semantic_escape_rebased.json \
   artifacts/formulation/evidence/semantic_escape_rebased.json
cp artifacts/worker-16/corpus_rebind/out/acceptance_pipeline_report.json \
   artifacts/formulation/evidence/acceptance_pipeline_report.json
```

or re-run the sanctioned tool in place (`python3 artifacts/formulation/tools/measure_semantic_escape.py`).
Either way the FROZEN revision must be bumped and re-hashed by the formulation lead.
Adoption alone still leaves `run_acceptance.py` at exit 1 until `W16R28-F2` is dispositioned.

## Falsifier

Refute any of: (a) a `run_acceptance.py` run at frozen bytes with the current frozen
evidence and unpatched tools that exits 0 (no rebase needed); (b) staged inputs differing
from the pinned `FROZEN.json` rev28 hashes; (c) two staged `measure_semantic_escape.py`
runs yielding different `semantic_escape_rebased.json` sha256; (d) the rebased corpus
applying a different mutation set than manifest `c102445df397` (mutant count/ids differ).

## Residual open items (not addressed here)

- `W16R28-F2` — canonical F1 stage-2 `R03`; lead/controller disposition (Option A/B).
- `W16R28-F3` — location-dependent `gate_test_report` hash.
- `W16R28-F4` — rev27 freeze-discipline observation.
