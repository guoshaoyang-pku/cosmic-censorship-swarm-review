# W055-A0-HF01-FIRING-01 — does the canonical runner fire HF-01 on the live ledger?

Worker: `worker-055`. Node: `A0`. Gate: `G-AUDIT`. Classes: the four frozen class ids.
No inbox card existed for `worker-055`; one bounded class-bound task was taken from the live
A0 contest (worker rule: propose one artifact-backed task, claim no completion).

## Question

`reviews/A0-review-worker-089.json` (A0-089-A, 2026-09-12T00:51:54+08:00) states:

> HF-01 conformance (`evaluation_rubric.yaml:174`) reads `claim.artifact_refs`, absent from
> all 62 `ledger/theorems.jsonl` rows incl. the 30 theorem rows; `audit_lib.py:189-191` +
> `audit_run.py:216` make that 30 false criticals and break the G-AUDIT `hard_failure_rate`
> criterion (`evaluation_rubric.yaml:149`).

The literature lead and workers 063/077 read the same artifacts as *not* firing HF-01 on
ledger rows (detector claim-scoped). The two readings cannot both be right; this task
measures which one the canonical code takes.

## Pins (measured before and after every run; drift refuses with exit 3)

| path | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `evaluation_rubric.yaml` (A0) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `artifacts/audit/audit_run.py` | `3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411` |
| `artifacts/audit/audit_lib.py` | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` |

`artifacts/audit/evaluation_rubric.yaml` is a symlink to the root A0 rubric, so the runner
reads the rubric of record.

## Method

Three independent tiers, all read-only on canonical paths:

1. **T0 canonical routing** — `census.py` re-implements the bucket predicate of
   `audit_run.scan_corpus` (`audit_run.py:81-121`) without importing it and classifies all
   62 ledger rows.
2. **T1 rubric-literal count** — counts rows satisfying the HF-01 antecedent text
   (`conclusion_type == theorem` and no `artifact_refs`).
3. **T2 detector + end-to-end** — calls the canonical `audit_lib.check_class_binding` on
   labelled probes, and runs the canonical CLI twice with `--quiet` (which suppresses the
   `lead-audit` event emitter):
   * `canonical_live/`: `--scan ledger` — the live ledger at the pin.
   * `canonical_controls/`: `--scan ledger tmp/w055_hf01_probe` — same ledger plus one
     labelled positive control claim (`PROBE-POS-W055`, theorem, no `artifact_refs`).

## Measured

| tier | quantity | value |
|---|---|---|
| T0 | ledger rows routed to `corpus['claims']` | **0** |
| T0 | ledger rows routed to `corpus['records']` | **62** |
| T1 | theorem rows | **30** |
| T1 | theorem rows without `artifact_refs` (no row has the field) | **30** |
| T2 | canonical run on ledger: HF-01 count / critical total | **0 / 0** |
| T2 | canonical control run: HF-01 count / `where` | **1 / `PROBE-POS-W055`** |
| T2 | `check_class_binding` positive probe (theorem, no refs) | HF-01 ×1 |
| T2 | `check_class_binding` negative probe (theorem, with refs) | HF-01 ×0 |
| T2 | ledger row without singular `class_id` forced through the detector | HF-02, never HF-01 |

Code path: the **only** HF-01 emitter is `audit_lib.py:189-191`, inside
`check_class_binding`; its **only** caller is `audit_run.py:233`, in the loop over
`corpus['claims']` at `:232`. Ledger rows carry `class_ids` (plural) + `statement_exact`,
so the routing predicate at `audit_run.py:96-119` sends them to `records` (a row without a
singular `class_id` would take the early `class_id not in classes` return and emit HF-02,
not HF-01). The line `audit_run.py:216` cited by A0-089-A is the `argparse --scan` default
declaration, not an HF-01 path.

## Verdict (advisory; worker events cannot move gates or status)

**A0-089-A_PARTIAL: COUNT CONFIRMED, MECHANISM REFUTED.**

* Confirmed: 30 of 62 ledger rows are `conclusion_type=theorem` with no `artifact_refs`
  field anywhere in the ledger. Under a reading that treats ledger *records* as claims, the
  HF-01 antecedent is satisfied 30 times.
* Refuted: the canonical runner does not emit those 30 criticals. It routes 0/62 rows to
  `claims`, and the canonical run at the pinned bytes returns HF-01 = 0, critical = 0. The
  detector is not inert: the same pipeline emits exactly one HF-01 for a labelled
  theorem-without-refs claim.
* Consequence for A0: A0-089-A is a rubric-text vs corpus-routing **scope ambiguity**, not a
  live false-critical defect in the canonical audit output. Whether HF-01 should cover
  theorem-typed ledger records is an A0-owner scope decision (PROTOCOL rule 1 governs claim
  *events*; ledger records are not events).

## Controls

* positive end-to-end (canonical CLI emits HF-01 for the probe), negative end-to-end (the 62
  ledger rows in the same run contribute 0),
* detector positive/negative and the no-singular-`class_id` routing probe,
* hash-drift guards in `census.py` and `assemble_report.py` (exit 3).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-055/a0_hf01_firing/census.py --out artifacts/worker-055/a0_hf01_firing/census.json
python3 artifacts/audit/audit_run.py --quiet --scan ledger \
  --out "$PWD/artifacts/worker-055/a0_hf01_firing/canonical_live"
python3 artifacts/audit/audit_run.py --quiet --scan ledger tmp/w055_hf01_probe \
  --out "$PWD/artifacts/worker-055/a0_hf01_firing/canonical_controls"
python3 artifacts/worker-055/a0_hf01_firing/assemble_report.py
```

Note: `--out` must be absolute (worker-038 S2a: relative `--out` crashes `audit_run.py`).

## Falsifier

Re-run the commands above at the pinned hashes. The adjudication is falsified if any of:
(a) `scan_corpus` routes ≥1 ledger row into `corpus['claims']` at `audit_run.py#3b27dd3fef7f`;
(b) the canonical ledger-scoped report contains an HF-01 violation whose `where` names a
ledger row; (c) the labelled positive control fails to produce exactly one HF-01; or
(d) any pin in the table above measures differently.

## Limitations / non-claims

* The full default scan over `artifacts/` (524 MB, 5044 json/jsonl files) exceeded a
  10-minute worker bound and was stopped; the contested finding is scoped to the canonical
  ledger, which the completed runs cover exactly.
* `canonical_live`'s runner-internal `gates: {G-AUDIT: pass}` is computed by
  `audit_run.gate_verdicts` over a claims-empty scoped corpus and is **not** a controller
  gate verdict; nothing here changes G-AUDIT, which stays pending.
* No gate verdict, no node status change, no `validation_status=passed`, no mathematics or
  physics claim; A0-089-A's other findings (B/C/D/E/F) are untouched.
