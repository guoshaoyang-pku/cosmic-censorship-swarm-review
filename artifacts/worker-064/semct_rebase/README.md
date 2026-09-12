# W064-SEMCT-REBASE-01 — semantic contract suite: rebased frozen controls, verified

Bounded class-bound worker task (`worker-064`, instance `worker-064-20260912T003008-968807`) taken
without an inbox card. Target: `schemas/semantic_contract_tests/` (calibration evidence routed to
**G-AUDIT**, node **A1**; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`).
This closes the `ADJ-CONTROL-STALENESS` repair loop opened by `W064-SEMCT-REBIND-01`
(`comms/outbox/worker-064.jsonl`, 00:29). **No canonical artifact was modified**; every repaired
byte is a proposal under this directory.

## Snapshot measured (no drift during the window, all three files byte-stable start→end)

| artifact | sha256 (12) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` |
| `schemas/semantic_contract_tests/manifest.json` | `b2e8bd17892b` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |
| `artifacts/formulation/KEY_MANIFEST.json` | `014e2d301978` |
| `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` |

Full snapshot pins: `snapshot/SNAPSHOT.json`; raw stage outputs: `raw/`.

## Baseline at the snapshot

- Three canonical schemas: **structural pass** (the earlier rev12 R22 defect is gone), C2/C0
  accepted by both semantic stages, **WCC rejected by both semantic stages on R03**
  (`binder '(q,t0)' absent from formal sentence`).
- Three frozen controls: **structural fail on R22 and R28** —
  R22 because the historical top-level key `revised_at_unused` is no longer in `KEY_MANIFEST`,
  R28 because the `finite_codimension_complement → residual_comeager` `direction: transfers` entry
  sits in `genericity.transfer_failures` (the `ADJ-CONTROL-STALENESS` cause).

## Rebase (proposal, machine-verified)

Two text-preserving edits per control, applied to worker-local copies:

1. **(A, R22)** move the single top-level line `revised_at_unused:` under `extensions:`.
2. **(B, R28)** delete the misplaced 8-line transfers entry from `genericity.transfer_failures`.

| control | old sha256 (12) | new sha256 (12) | removed lines |
|---|---|---|---|
| `control_comment_only_composite.yaml` | `a6ad2638dc99` | `ce8b15e22722` | 8 |
| `control_conforming_base.yaml` | `7b910cf34e64` | `253c28e03c53` | 8 |
| `control_quoted_forbidden_phrase.yaml` | `687fd6971304` | `2399f5752af1` | 8 |

Verified minimal: for each control the transformed YAML **equals the expected transform exactly**
(`exact_expected_transform=true`), the unified diff contains only the recorded 1+8 removed and 2
added lines (`edits_exact=true`), and the mutated 32-fixture corpus is untouched.

## Verification results

| check | result |
|---|---|
| rebased controls vs structural / semantic baseline / hardened | **pass / accept / accept** (3/3) |
| sensitivity mutants rejected | 3× restore-stale-bytes → `R22,R28`; comment→data → `R13,R31`; unquote → `R13,R22` (5/5) |
| S1 full suite: rebased controls + refreshed pins | executes, exit 3; mutants **32/32 structural, 11/32 baseline, 32/32 hardened**; frozen controls accepted **True**; canonical controls accepted **False** (WCC R03); `valid_for_calibration=false` |
| S0 full suite: unmodified manifest | exit 2, 3 integrity errors (stale canonical pins) |
| S2 negative control: rebased bytes, pre-rebase control pins | exit 2, exactly 3 control sha mismatches |
| S3 alternative strategy: delete `revised_at_unused` instead of nesting | structural accept 3/3 |

**Conclusion:** the control rebase clears `ADJ-CONTROL-STALENESS` — with it the suite's frozen
controls pass every stage and the mutant numbers reproduce exactly. The suite still cannot return
exit 0 because of a *second, independent* blocker owned by formulation: the adopted semantic
auditor rejects canonical **WCC on R03**. The runner reports this as
`blocking_adjudication=[]` while `valid_for_calibration=false`, which misdirects the repair to the
controls (F-REBASE-6).

## Findings (each with its falsifier)

- **F-REBASE-1** — controls fail structural on R22+R28; canonicals pass structural, WCC fails
  semantic R03. *Falsifier:* a control passing / failing other rules, a canonical failing
  structural, or WCC accepted by both semantic stages at the pinned bytes.
- **F-REBASE-2** — minimal rebase is the two recorded edits; transformed YAML equals the expected
  transform exactly. *Falsifier:* any extra YAML diff or fixture change.
- **F-REBASE-3** — rebased controls pass all three stages; all five sensitivity mutants are
  rejected. *Falsifier:* a rebased control rejected by any stage or a mutant not rejected.
- **F-REBASE-4** — full-suite S0/S1/S2 numbers as above. *Falsifier:* different exit codes, mutant
  counts, acceptance flags or validity on re-run at the pinned bytes.
- **F-REBASE-5** — residual validity blocker is WCC R03 (owner lead-formulation / semantic-auditor
  owner), not the controls. *Falsifier:* a semantic run accepting WCC at the pinned bytes.
- **F-REBASE-6** — runner emits `blocking_adjudication=[]` for a conforming-canonical rejection.
  *Falsifier:* a run naming the canonical rejection in `blocking_adjudication`.

## For the lead (owner `astra-lead-formulation`)

1. Apply `rebase_patch.json` → copy `rebased_controls/*` over the three fixtures, repin
   `manifest.controls[].sha256` and `manifest.conforming_canonical_controls[].sha256`
   (`manifest_rebased.json` is the worker-local example).
2. Resolve the WCC R03 semantic finding (formal sentence / binder `(q,t0)`), then re-run
   `run_contract_tests.py`; expect exit 0 and `valid_for_calibration=true`.

## Limits / not claimed

Measurements are bound to the pinned snapshot bytes. No gate verdict, no node completion, no
mathematical verdict on any schema, no modification of any canonical artifact, and no
recommendation on whether the R22 key should be renamed, restored to `KEY_MANIFEST`, or nested —
the nesting is only the strategy verified here (deletion also verified as S3). Worker events cannot
set `done`, `passed`, or a gate verdict.

## Files

| file | what |
|---|---|
| `semct_rebase_audit.py` | deterministic harness (snapshot → baseline → rebase → verify → mutate → simulate) |
| `report.json` | full structured report, findings, falsifiers, raw verdicts |
| `rebase_patch.json` | machine-applicable patch (control bytes, pin changes, residual blocker) |
| `rebased_controls/` | the three rebased control fixtures |
| `manifest_rebased.json` | worker-local suite manifest with refreshed pins |
| `snapshot/` | byte snapshot + `SNAPSHOT.json` pins of every input |
| `raw/` | raw stage JSON outputs |
| `work/` | S0/S1/S2/S3 simulation trees, observed verdicts, stdout |
