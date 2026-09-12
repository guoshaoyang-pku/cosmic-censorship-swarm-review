# W092-HELDOUT10-THIRDPARTY-REPL-01 — independent third-party replication of FORM-HELDOUT-10

- **worker**: `worker-092` (one bounded execution pass; no inbox card for this slot, self-selected
  per the fleet convention — no card newer than the pass-08 set exists for worker-092)
- **node / gate**: `A1` / `G-CLASSBIND`
- **class_ids**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **authority**: worker measurement evidence only. No node completion, no
  `validation_status=passed`, no gate verdict, no theorem.
- **target**: `artifacts/heldout/heldout-10/` (corpus author `worker-084`), the preserved corpus
  behind the substantive G-CLASSBIND blocker `lead-form-20260912T011516-124` and the
  `FORM-HELDOUT-10` headline measurement.

## Why this run exists

`FORM-HELDOUT-10` reports that on the informative C2+C0 arms the two-stage pipeline catches
**0 of 26** informative mutants (union escape 1.0), so the semantic stage carries no class-binding
signal for the classes it is meant to protect. The corpus's own `verify/` re-run was executed by
its author (`worker-084`, `W084-HELDOUT10-INDEP-01`, declared as a re-run), and the formulation
lead's check is owner-side. No non-author, non-owner reproduction existed. This run is that
reproduction: fresh driver, hash-first, read-only on all canonical and corpus bytes.

## Independence basis (declared, not implied)

- Does **not** import `build_corpus_10.py`, `run_heldout_10.py` or
  `verify_heldout_10_independent.py`. It parses `manifest.json`, re-hashes every fixture, invokes
  the two stage tools as subprocesses, and derives every verdict and aggregate itself.
- Writes only under `artifacts/worker-092/heldout10_repl/`.
- Uses the stage tools **as-is**: this replicates the pipeline's verdicts; it does not re-implement
  the rules.

## Preflight (hash-first)

| item | measured | verdict |
|---|---|---|
| `manifest.json` | `d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236` | matches preregistered hash |
| `report.json` | `5629e2a69c8664abe4b322281318bf5ca0754967cb87607c5818da7e015efd35` | matches preregistered hash |
| `raw/raw_verdicts.json` | `b3480625da10cd3c6b3a69b7d400b20094fb500d308bbd7c2c009f672a9f44a3` | matches preregistered hash |
| stage A `check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` | matches manifest |
| stage B `spec_conformance_audit.py` | `c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec` | matches manifest |
| stage A key manifest | `014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a` | matches manifest |
| canonical pins F1/F2a/F2b + taxonomy + rule_spec | all `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` / `0abb9ed8a961` / `40f9bb9e657b` | 0 mismatches |
| 40 fixtures | re-hashed individually | 0 mismatches |
| base copies vs live canonicals | 3/3 | byte-identical |

## Method

For each of 40 fixtures (3 frozen canonicals + 4 authored controls + 33 mutants), exactly one
stage A and one stage B subprocess; 80 invocations total, 7.3 s of stage time, 0 crashes.
`structural escape = stage A pass`, `semantic escape = stage B accept`,
`union escape = accepted by both stages` (the corpus's own convention, re-derived here).

## Result — the headline reproduces exactly

| population | mutants | structural escape | semantic escape | union escape | union caught | preserved union escape |
|---|---:|---:|---:|---:|---:|---:|
| all mutants | 33 | 1.0 | 0.7879 | **0.7879** | 7 | 0.7879 |
| informative C2+C0 only | 26 | 1.0 | 1.0 | **1.0** | **0** | 1.0 |
| WCC arm (non-informative) | 7 | 1.0 | 0.0 | 0.0 | 7 | 0.0 |

- **Per-fixture agreement: 40/40 fixtures, 0 disagreements** on structural/semantic/union escape
  and on both stages' `failed_rules` sets, against the preserved `raw/raw_verdicts.json`.
- **All 26 informative mutants escape both stages** (13 families × 2 arms): conclusion-content
  erasure, conclusion-polarity inversion, containment reversal, development-topology weakened,
  end-structure contradiction, equivalence inflation, extension-predicate weakened,
  f0-binding stale hash, known-obstruction erased, natural-language inversion, schema-falsifier
  erasure, Sobolev threshold lowered, source-status flip.
- The 7 WCC-arm "catches" are **R03-only** on every fixture — the same rule that rejects the
  untouched frozen WCC canonical — so they carry no class-binding signal. Strict H5 is `false` for
  exactly that pre-registered reason, and it was reproduced unfavourably rather than excused.
- Authored controls 4/4 accepted by both stages; frozen C2/C0 canonicals accepted by both;
  frozen WCC canonical passed stage A, rejected by stage B on `R03` only.
- **Postflight drift: none.** Every canonical pin, the manifest/report/raw hashes and both stage
  tools re-hash identically after the run. In particular stage B stayed at `c79d8ab8440a`
  throughout.

`validity.replication_valid = true` in `report.json`: 0 fixture-hash mismatches, 0 per-fixture
disagreements, controls as declared, strict H5 holds, 0 drift.

## Findings (worker-level, informational)

- **F-092-H10-01 (info)**: `FORM-HELDOUT-10`'s informative-arm result is independently
  reproducible at the frozen pins; the `lead-form-20260912T011516-124` blocker is not an artifact
  of the corpus author's own pipeline. Any future claim that the rev13 prose repair closed the
  leak is falsified by this run.
- **F-092-H10-02 (governance, info)**: the corpus's `verify/` artifact is author-side
  (`verifier: worker-084`); this run is the first non-author, non-owner reproduction. Independence
  of future held-out measurements should be stated explicitly, not inferred from the word
  "independent".
- **F-092-H10-03 (governance, info)**: stage B is unpinned in FROZEN rev29
  (`lead-form-20260912T011516-123`). This run measured `c79d8ab8440a` before and after with no
  drift, but any adoption of a repaired R03 changes gate-relevant evidence with no pinned byte
  moving unless the tool hash is pinned in the same FROZEN revision.
- **F-092-H10-04 (scope, info)**: the WCC arm cannot contribute evidence while R03 rejects the
  untouched canonical. Only the 26 informative C2/C0 mutants are a valid measurement basis, as the
  corpus declares.

## Falsifiers (what would overturn this)

- Re-run `replicate_heldout10.py`: any per-fixture verdict disagreement against
  `raw/raw_verdicts.json`, any fixture whose measured sha256 differs from the manifest, or any
  mid-run move of a pinned canonical or stage tool falsifies this replication.
- A repaired stage B under which any of the 26 informative mutants is caught on a non-R03 rule
  falsifies the *current-instrument* escape claim (and would be the wanted outcome).
- `report.json` records the full per-fixture table, so a single-fixture counterexample is directly
  checkable.

## Limits

- Stage tools are used as-is; the rule implementations are not independently re-implemented.
- Fixtures are not re-authored; the corpus's fixture choice is taken as given.
- No claim is made about whether the leak is a schema defect or a rule-engine gap; this run
  measures pipeline behaviour only.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-092/heldout10_repl/replicate_heldout10.py
# exit 0 = zero disagreement + zero drift; exit 3 = disagreement/drift found and reported
```
