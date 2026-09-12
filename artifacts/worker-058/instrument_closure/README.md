# W058-INSTRUMENT-CLOSURE-07 — the G-FORM acceptance instrument is not hash-closed

**Worker** worker-058 · **Nodes** F1, F2a, F2b · **Classes** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN · **Gate context** G-FORM · **Created** 2026-09-12T01:3x+08:00
**Authority** worker evidence only — no gate verdict, no node status, no validation promotion.

## Why this task

The formulation lead's 01:15:16 lifecycle-08 blocker (`INSTRUMENT GOVERNANCE GAP`) reported that
the acceptance pipeline is only half hash-bound: `run_acceptance.py` is pinned in FROZEN rev29,
but the stage-2 rule engine it executes is not. This task turns that single observation into a
complete, machine-checked closure audit: *which bytes can move a G-FORM acceptance outcome, and
are they pinned?* — plus a planted-tamper experiment proving the gap is outcome-changing.

## Result

| measurement | value |
|---|---|
| acceptance-scope closure | **CLOSURE_GAP** |
| reached paths | 117 |
| pinned OK / drifted / unpinned | 36 / **1** / 79 |
| effect-capable unpinned | **71** = 2 code + 69 corpus |
| synthetic selftest | **10/10** (`sensitivity_selftest.json`) |
| planted-tamper flip | **FLIP_CONFIRMED**, 12/12 checks |
| canonical bytes written by this task | none (`I_canonical_unchanged = true`) |

## The 71 outcome-changing unpinned bytes

| tier | paths | why it matters |
|---|---|---|
| `verdict_code` | `artifacts/worker-06/spec_conformance_audit.py` (live `c79d8ab8440a`) | stage-2 semantic engine; subprocess-executed by the pinned `run_acceptance.py:25` and `measure_semantic_escape.py:29`; **0 occurrences** in `FROZEN.json` |
| `verdict_code` | `artifacts/formulation/tools/check_variant_registry.py` (live `8c7ef46f11db`, declared `c471da4b7be9`) | **live pin drift**: file written 2026-09-12T01:21:56, after the 00:57:26 rev29 freeze; `verify_frozen.py` now exits 1 on the canonical tree |
| `corpus` | 33 × `artifacts/formulation/evidence/rebased_fixtures/*.yaml` | the mutant corpus `run_acceptance.py:82` globs and judges |
| `corpus` | 32 × `artifacts/worker-06/semantic_fixtures/*.yaml` + 3 controls + `manifest.json` | the source corpus the unpinned engine globs at `spec_conformance_audit.py:577,623` and the rebase tool reads at `measure_semantic_escape.py:25` |

Full list, per-path roles, referencing tools and measured hashes: `closure_manifest.json`.
The all-pinned-tools scope (73 gaps, includes provenance/repair tools) is in
`closure_manifest_all_scope.json`.

## Proof the gap is outcome-changing (`flip_probe.json`)

Isolated sandbox built from the live pins (canonical read-only):

1. baseline `run_acceptance.py --json` → verdict FAIL because canonical F1
   (`af_wcc_vacuum.yaml`) is **semantically rejected** (R03) by the live unpinned engine, while
   the mutant union is 31/31. The pinned `acceptance_pipeline_report.json` claims PASS with all
   canonical rows ok — it does not bind the live engine+schema bytes.
2. replace the unpinned engine with an always-accept stub → canonical F1 flips fail→pass,
   semantic mutant catches drop **11 → 0**, union drops **31/31 → 30/31**.
3. at the same time **0 of 50 pinned bytes move**, `verify_frozen.py` still exits **0**, and the
   closure guard still reports the engine as `UNPINNED`.
4. remedy control: pin all 70 sandbox gap paths → `closure_check.py --strict` exits **0 (CLOSED)**;
   re-tamper the now-pinned engine → exits **1** with `PINNED_DRIFT`.

## Second live inconsistency (preflight stale)

`artifacts/formulation/evidence/semantic_escape_rebased.json` declares
`base_sha256 = 1bb78ce9b357…` while live `schemas/af_scc_c0_vacuum.yaml` is `b2ab6acb2bbe…`.
`run_acceptance.py::preflight` compares exactly these two and returns exit 3 on mismatch, so the
canonical acceptance pipeline currently **fails closed as stale**; the pinned PASS report cannot be
reproduced at the live pin without regenerating the corpus with the unpinned engine.

## Remedy surface for the next freeze (owner action, not taken here)

One freeze break that, in the same revision: pins the stage-2 engine at its measured hash; pins
`artifacts/worker-06/semantic_fixtures/` (manifest + fixtures + controls) and
`artifacts/formulation/evidence/rebased_fixtures/` (or records them as generated-and-verified);
regenerates `semantic_escape_rebased.json` at the live C0 and pins the regenerated evidence;
absorbs or reverts the `check_variant_registry.py` drift; then re-runs
`closure_check.py --scope acceptance --strict` and requires CLOSED, and re-runs the acceptance
pipeline requiring PASS with all canonical rows ok.

```bash
# closure guard (read-only; exit 1 on any effect-capable unpinned path)
python3 artifacts/worker-058/instrument_closure/closure_check.py --root . --scope acceptance --strict
# synthetic controls
python3 artifacts/worker-058/instrument_closure/closure_check.py --root . --selftest
# outcome-flip experiment (writes only under artifacts/worker-058/instrument_closure/)
python3 artifacts/worker-058/instrument_closure/flip_probe.py
# report reassembly
python3 artifacts/worker-058/instrument_closure/finalize_report.py
```

## Findings

See `report.json` → `findings` (W058-IC-01…07). Severity: IC-01/02/03/04/05/06 hard,
IC-07 info.

## Boundary and falsifier

Static reachability (local `.py` refs, `Path` joins, literal glob patterns) plus one sandbox
experiment; paths reached only through computed runtime values are not discovered. The sandbox
FROZEN manifest is a simulation, not a publication. The `check_variant_registry.py` drift is
reported as an externally measured event — authorship, authorization and consequence belong to the
controller.

**Falsifier.** A reader shows (a) the stage-2 engine hash is pinned in FROZEN rev29 under another
path/alias, (b) an outcome-changing reachable path outside the reported closure set, (c) the
baseline/tampered acceptance reports are not reproducible from the cited hashes, (d) the remedy
control does not close the strict guard, or (e) a canonical byte was written by this task.
