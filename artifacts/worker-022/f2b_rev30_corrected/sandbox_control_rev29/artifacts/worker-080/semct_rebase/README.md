# W080-SEMCT-REBASE-01 — executed candidate resolution of ADJ-CONTROL-STALENESS

Worker: `worker-080` (bounded instance, 2026-09-12). Classes: **AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN**. Node: A1. Gate: G-AUDIT.

**Status: worker-level candidate patch + measurements. No gate verdict, no node status,
no canonical file written.**

## Question

The G-AUDIT calibration suite `schemas/semantic_contract_tests/` cannot be used at the
current frozen revision. Two mechanical blockers were known:

1. its three `conforming_canonical_controls` pins predate the FROZEN rev27/28 republish
   (runner exits 2, integrity failure, no output) — measured again by worker-064;
2. its three frozen controls embed the old corpus-base layout, so the structural gate
   rejects them — routed to lead-formulation as **ADJ-CONTROL-STALENESS** with the
   instruction "rebase the control layouts to the current canonical (mutants stay
   frozen — that changes only controls)".

This task *builds and executes* the rebase candidate, read-only on every canonical path.

## Method

`rebase_semct.py` stages a minimal repo subset (suite + fixtures, the three canonical
schemas, `check_class_schema.py`, `rule_spec.json`, `KEY_MANIFEST.json`,
`spec_conformance_audit.py`) into a sandbox, then runs the **canonical runner unmodified**
under pre-registered expectations, with targeted negative controls. Every input is hashed
before and after; the run recorded **no input drift**.

Two minimal, comment-preserving text edits per control (validated to leave the YAML data
model byte-equal except the intended removals):

| edit | what | why |
|---|---|---|
| E1 | delete the **duplicated** `finite_codimension_complement → residual_comeager` row from `genericity.transfer_failures` (the correct row stays in `transfer_holds`) | structural **R28** rejects a `transfers` row in `transfer_failures` |
| E2 | delete the top-level `revised_at_unused` key | unknown to the regenerated `KEY_MANIFEST` → structural **R22** |

Rebased controls: `patched_controls/*.yaml` (`b781d41d…`, `14c2b78b…`, `44030ca4…`).
Rebased manifest: `manifest_rebased.json` (`7f960f3c…`).

## Runs (FROZEN rev28; canonical F0 `0abb9ed8…`, F1 `cce9c601…`, F2a `5476a3f2…`, F2b `55d0a1ea…`)

| run | change | exit | controls all-stage | valid | mutants (struct/base/hard) |
|---|---|---:|---:|---|---|
| R0 | canonical manifest as-is | **2** | – | – | integrity failure: exactly 3 stale K-pins |
| R1 | pins rebound only | 3 | 0/3 | false | 32/32, 11/32, 32/32 |
| **R2** | pins rebound + E1 + E2 | 3 | **3/3** | false | 32/32, 11/32, 32/32 |
| R3a | E2 undone (row removed) | 3 | 0/3 | false | unchanged; controls fail **R22** |
| R3b | E1 undone (key removed) | 3 | 0/3 | false | unchanged; controls fail **R28** |
| R4 | E1+E2, stale row re-inserted | 3 | 0/3 | false | unchanged; controls fail **R28** |
| R5 | R2 re-run, fresh sandbox | 3 | 3/3 | false | per-test verdicts identical to R2 |

**ADJ-CONTROL-STALENESS question: answered yes.** After the three pin rebinds + E1 + E2 the
three frozen controls pass all three stages (R2, R5), the 32-mutant corpus is byte-untouched
and its counts are unchanged in every run, R3a/R3b show each edit is necessary, and R4 shows
the structural gate still fires on the stale row when re-inserted.

## Remaining blocker found by this task (new)

`valid_for_calibration` is *still* false after the rebase, for an independent reason:
conforming-canonical control **SCT-K03** — `schemas/af_wcc_vacuum.yaml` at rev12
(`cce9c601…`) — is rejected by **both semantic stages on R03 alone**:

> `binder '(q,t0)' absent from formal sentence`

`probeB` (`r03_lexical_probe.py`, report `9a0498bb…`) isolates it:

- the binding **structural gate passes** rev12; the rejection is from the worker semantic
  auditor (`spec_conformance_audit.py` `c79d8ab8…`), so F1 is not structurally defective;
- rev12 changed the D5 binder from `q` to the composite `(q,t0)` and spelled the tail predicate
  out in `quantifiers.formal` as `not exists q in I+ and t0 in [0,T) ...`; R03 requires the
  **literal binder token**, so the composite is "absent";
- the pinned rev11 (`9a8bd4c9…`, binder `q`) and the pre-rev11 snapshot (`b65fcc0f…`) are
  **accepted** by the same stage: the trigger entered with rev12;
- a **notation-only rewrite** of that clause to the D5-relative form
  (`not exists (q,t0) in D5 with ...`) clears R03 with **every other check status unchanged**;
- a scratch mutant with a genuinely absent token (`(q,t0,ABSENT)`) still **fails R03**.

So the rev12 rejection is a **lexical false positive** of a worker-side checker against a
formal sentence that is *more* explicit than rev11's (the rev12 change is the HF-06 tail
predicate fix). Per CF-4 policy the checker flags; it does not author. Two secondary gaps
surface with it:

- the runner's `validity.blocking_adjudication` list is **empty** in this case (it names
  ADJ-CONTROL-STALENESS only for the frozen-control basis), so a rejected
  conforming-canonical control is not routed to any adjudication item;
- the suite therefore cannot be cited as current-revision G-AUDIT calibration evidence yet,
  even though the control basis is now mechanically clean.

## What the owner can adopt

1. **ADJ-CONTROL-STALENESS**: apply E1+E2 to the three files under
   `schemas/semantic_contract_tests/fixtures/controls/` (or copy `patched_controls/*.yaml`)
   and re-pin the six manifest sha256 values — the ready values are in
   `manifest_rebased.json` and `control_edits.json`.
2. **F1 R03**: either make R03's binder check resolution-aware (accept a composite binder
   whose components occur in `formal`, or resolve binders through `quantifiers.domains[d].definition`)
   or record the lexical-false-positive adjudication for rev12; do not edit F1's formal
   sentence to satisfy a lexical check (CF-4).
3. **Runner gap**: extend `validity.blocking_adjudication` to name a rejected
   `conforming_canonical` control.

## Falsifier

Re-run `rebase_semct.py` and `r03_lexical_probe.py` at the pinned hashes: any run whose exit
code, integrity-error count, control acceptance, mutant counts, or per-test observed verdicts
differ from the recorded grades falsifies the corresponding clause; any input-hash drift voids
the report at those paths; a rebased control accepted while still carrying the duplicated row
or `revised_at_unused` falsifies that edit's necessity; a rev12 semantic accept, a rewrite that
still fails R03, a rewrite whose non-R03 check statuses change, or an absent-token mutant that
passes R03 falsifies the lexical-false-positive conclusion.

## Files

| file | sha256 (16) | role |
|---|---|---|
| `rebase_semct.py` | `b306b795ee20723d` | harness: staged runs R0–R5, edits, negative controls |
| `report.json` | `05856c58164b6383` | final report (raw + root-cause annotation) |
| `report_raw_harness.json` | `0bef6f9592c3875f` | untouched raw harness measurements |
| `r03_lexical_probe.py` | `2b609251770457e7` | probe B |
| `r03_probe_report.json` | `9a0498bbaf632076` | probe B report |
| `control_edits.json` | `60d6758e98625813` | exact edits + data-model validation per control |
| `manifest_rebased.json` | `7f960f3c4fc2a559` | manifest with all six pins rebound |
| `patched_controls/*.yaml` | `b781d41d…`, `14c2b78b…`, `44030ca4…` | rebased control fixtures |
| `runs/` | – | per-run stdout + `observed_verdicts.json` copies |
| `finalize_report.py` | `773e02255ae47e94` | annotation step (raw preserved) |

Reproduce: `python3 artifacts/worker-080/semct_rebase/rebase_semct.py` (exit 0 iff every
pre-registered expectation holds; the two R2 rows are falsified *by the finding above* and
documented in `report.json.annotation`) and
`python3 artifacts/worker-080/semct_rebase/r03_lexical_probe.py` (exit 0).

## Limits

- Worker-side candidate only: no canonical path was modified; `ADJ-CONTROL-STALENESS` and any
  F1 change remain lead-formulation decisions.
- `valid_for_calibration` is a mechanical property of the suite's own runner; it is not a gate
  verdict and says nothing about mathematical truth or non-vacuity.
- R03 is a worker-side auditor rule, not the binding gate.
- All measurements are at the pinned FROZEN rev28 bytes; the sandbox staged copies, and input
  hashes were stable across the run.
