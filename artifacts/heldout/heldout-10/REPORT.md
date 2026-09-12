# FORM-HELDOUT-10 — re-issued held-out measurement on the LIVE rev13 / FROZEN rev29 bytes

- **worker**: `worker-084` (one bounded execution pass)
- **class_ids**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **node / gate**: `A1` / `G-CLASSBIND`
- **authority**: worker measurement evidence only. No node completion, no
  `validation_status=passed`, no gate verdict, no theorem.
- **supersedes**: `FORM-HELDOUT-09` (worker-084), which was terminally INVALID: its card pins went
  stale on 4/6 paths (rev12→rev13, FROZEN rev28→rev29) and its strict H5 failed on the same R03
  instrument defect reported here.

## Why this corpus exists

The heldout-09 blocker required a card re-issued against FROZEN rev29 with the corpus rebuilt from
the rev13 bytes. No new inbox card was issued to worker-084, so this pass self-claims that
successor task under the swarm's one-bounded-class-bound-task rule, builds a **fresh** corpus
(`artifacts/heldout/heldout-10/`), and pre-registers against the **live** bytes only. The four
stale card pins are recorded verbatim in `manifest.json → card_pin_staleness` and are not used.

## Pre-registration (before any fixture stage run)

| item | value |
|---|---|
| `manifest.json` sha256 | `d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236` |
| FROZEN.json | rev **29**, `815e08079aef…` (frozen_at 2026-09-12T00:57:26+08:00) |
| F1 `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2…` |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3…` |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe…` |
| stage A `check_class_schema.py` | `000e09e46b2f…` |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a…` (unchanged) |
| mutants / families / controls | **33 / 19 / 7** (3 frozen canonical + 2 conforming + 2 negated-phrase) |

`known_calibration_defect` is recorded at freeze time: the untouched frozen F1/WCC canonical is
**rejected by stage B on R03 only** (literal-substring binder match), so the WCC arm is declared
non-informative *in advance*. Strict H5 is still evaluated and reported, unfavourably if it fails.

Two new mutant families target the exact axes the rev13 delta touched:

- `f1-visibility-equivalence-denied` (m30, m31 — W arm): revert `visibility.definition` and
  `class_identity_variants[0].relation` to the refuted rev12 "strictly STRONGER / not equivalent"
  reading;
- `f0-binding-stale-hash` (m32, m33 — C2/C0 arms): restore the stale rev12
  `consistency_evidence_sha256` `675a99d0d25b`, undoing the rev13 evidence-binding refresh.

## Result (both stages run exactly once per fixture; raw verdicts retained)

| population | mutants | structural escape | semantic escape | **union escape** | union caught |
|---|---|---|---|---|---|
| all mutants | 33 | 1.0 | 0.7879 | **0.7879** | 7 |
| informative arms only (C2+C0) | 26 | 1.0 | 1.0 | **1.0** | **0** |
| WCC arm (non-informative) | 7 | 1.0 | 0.0 | 0.0 | 7 (all R03-only) |

- **Strict run validity: `false`** — sole reason: `control af_wcc_vacuum.yaml rejected: stage B
  reject ['R03']`, the pre-registered instrument defect. No fixture was tampered, no pin moved
  during the run, manifest hashed before any fixture stage run.
- The 7 WCC-arm stage-B "catches" are **spurious**: every one fails R03 only, the same rule that
  rejects the untouched canonical. They carry no class-binding signal.
- The 4 authored controls and the frozen C2/C0 canonicals pass both stages, so the informative-arm
  escape is **not** format domination.
- New family `f0-binding-stale-hash`: **2/2 escape both stages** (neither stage reads `f0_binding`).
- New family `f1-visibility-equivalence-denied`: both mutants land in the non-informative WCC arm;
  their R03 rejection is the instrument defect, not detection.

## Replication vs heldout-09

| | heldout-09 (rev12/rev28) | heldout-10 (rev13/rev29) |
|---|---|---|
| informative mutants | 24 | 26 |
| informative union escape | 1.0 | 1.0 |
| strict valid | false (R03) | false (R03) |

Same direction, same magnitude, fresh fixtures, fresh base bytes: **the rev13 prose repair did not
close the C2/C0 leak**, and the R03 instrument defect is unchanged.

## Falsifiers

- Re-run `run_heldout_10.py` at the recorded manifest and pin hashes: any per-fixture verdict
  disagreement, or a stage-B accept of the frozen WCC canonical at `d9cebb9404b2`, falsifies.
- A repaired stage-B R03 plus a re-run of this preserved corpus would test whether the WCC arm
  carries real signal; a non-R03 catch of any informative-arm mutant falsifies the 1.0 escape.

## Artifacts (sha256)

| artifact | sha256 |
|---|---|
| `manifest.json` | `d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236` |
| `report.json` | `5629e2a69c8664abe4b322281318bf5ca0754967cb87607c5818da7e015efd35` |
| `raw/raw_verdicts.json` | `b3480625da10cd3c6b3a69b7d400b20094fb500d308bbd7c2c009f672a9f44a3` |
| `checkpoint.json` | `11b0dc1b57189e2010d3c91236811fa91983be86c9720b7351152c92655ef287` |
| `findings.json` | `874472a1364d5b92c361c1717737f5820f311ffaddfb1798c8713e6b48f8a3f1` |

Read-only discipline: every write is under `artifacts/heldout/heldout-10/`; no pinned canonical
path, stage tool or heldout-09 fixture was modified.
