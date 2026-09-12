# W087-GFORM-STAGE2-BINDING-01 — stage-2 instrument binding measurement

Worker: `worker-087` (no inbox card; self-selected bounded class-bound task).
Node: `F1,F2a,F2b`. Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`. Gate: `G-FORM`.
Run window: 2026-09-12 01:19–01:23 (+08:00). Read-only on every canonical path.

## Question

At FROZEN rev29 `815e08079aef`, is the stage-2 semantic rule engine
`artifacts/worker-06/spec_conformance_audit.py` bound to the frozen manifest by path or by
hash — or does a G-FORM-relevant verdict depend on bytes that no pin covers?

Trigger: `lead-form-20260912T011509-123` (INSTRUMENT GOVERNANCE GAP) and controller
`CF-32`/`REC-36`/`REC-41` plus assignment `astra-life08-stageb-r03` (worker-006, R03 binder fix
in the same stage-B tree).

## Measured configuration (all hashes sha256, live bytes at the pins above)

| item | hash | state |
|---|---|---|
| `artifacts/worker-06/spec_conformance_audit.py` (stage 2) | `c79d8ab8440a…` | **not a key of FROZEN.json.files** (50 pins, 14 `.py`); 0 occurrences in FROZEN.json |
| `artifacts/formulation/tools/run_acceptance.py` | `e544c36d2d16…` | pinned; resolves stage 2 by **path only** (line 10); its single `sha256` call (line 61, `preflight`) is over the C0 corpus base, never the engine |
| `artifacts/formulation/evidence/acceptance_pipeline_report.json` | `9b7d6c8208d3…` | pinned; `stages` records only the two stage **paths**, no instrument hash |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `7e44de0e3906…` | pinned; declares `w06_sha256 = c79d8ab8…` (written by `measure_semantic_escape.py:86`) — **no pipeline tool reads or compares it** |
| `runtime/state/artifact_hashes.json` | `b692ad72…` → `80191669…` (live) | no entry for the stage-2 path or hash |

## Decisive sensitivity probe (sandbox only; live engine never written)

Same input bytes for both arms: `schemas/af_wcc_vacuum.yaml` `d9cebb9404b2`.

| arm | engine | verdict | failed_rules |
|---|---|---|---|
| K1 | live-bytes copy `c79d8ab8…` | `reject` | `['R03']` — `binder '(q,t0)' absent from formal sentence` |
| K2 | one-line mutated copy `5273ae2f…` | `accept` | `[]` |
| K3 | mutated copy, mangled F1 control `be556ce4…` | `reject` | `['R03']` |
| K4 | live copy, mangled F1 control | `reject` | `['R03']` |

The K2 mutation relaxes only the literal binder-containment predicate to also accept a tuple
binder whose component tokens occur in `quantifiers.formal`; diff is one line (recorded in
`report.json`). It is a **sensitivity probe, not a proposed fix** and not an adopted instrument.

## Result

- Pre-registered literal verdict: **NOT_CONFIRMED**, because hypothesis H2 as written ("the stage-2
  hash appears in no pinned artifact body") is falsified by the single provenance field
  `w06_sha256` in the pinned, stale corpus file. Per the pre-registered decision rule, one false
  hypothesis blocks `PIN_GAP_CONFIRMED`.
- Operative gap: **CONFIRMED** (`operative_gap_confirmed = true`) on H1, H3, H3b, H4, H5 plus all
  eight control checks and zero pin drift: the engine is unpinned, the one declaration of its hash
  is unverified, and editing only that unpinned file flips the F1 stage-2 verdict from reject to
  accept while all 50 FROZEN pins stay byte-stable. The formulation lead's blocker
  `lead-form-20260912T011509-123` is independently confirmed as stated; the refinement is
  "declared-but-unverified in one pinned evidence file", not "unreferenced anywhere".
- Note: the pinned corpus that carries the declaration is itself stale per CF-32
  (`base_sha256 1bb78ce9` vs live C0 `b2ab6acb`), so it is not current gate evidence.

## Controls

K1 baseline reject, K1b/K2b normalized double-run determinism (timestamps excluded), K2 flip,
K3/K4 fail-closed on mangled input, K5 no pin drift (11 declared pins re-measured), K6 engine
identity (sandbox baseline = live; mutant differs) — **8/8 ok**.

## Falsifier

Falsified if: the stage-2 path is a key of `FROZEN.json.files` with matching hash; the stage-2 hash
occurs in FROZEN.json; a pipeline tool compares `w06_sha256`/`gate_sha256` before execution; K2
fails to flip the F1 verdict on byte-identical input at the same pins; or any declared pin moves.
A rev30 that pins the engine path+hash, or a `run_acceptance.py` that fails closed on a stage-2
hash mismatch, voids this measurement at that revision.

## Authority limits / non-claims

Worker-level measurement only: no node status, no gate verdict, no `validation_status=passed`.
No canonical file was written (schemas, FROZEN.json, run_acceptance.py, spec_conformance_audit.py,
acceptance report, taxonomy all byte-stable). No claim about the mathematical correctness of R03
or about the proposed binder fix; the sandbox mutation demonstrates pin dependence only.

## Reproduce

```bash
python3 artifacts/worker-087/stage2_binding/verify_stage2_binding_087.py   # exit 1 = literal NOT_CONFIRMED, operative gap true
```

Outputs: `report.json` (machine record), `runs.json` (raw engine captures),
`sandbox/artifacts/worker-06/spec_conformance_audit.mutant.py` (probe only).
`AMENDMENT-01.json` records the pre-run reclassification of the live registry from pin to live
input after the first harness run aborted on its movement.
