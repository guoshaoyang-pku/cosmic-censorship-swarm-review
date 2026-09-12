# W036-CLASSSEP-DISJ-01 — class_ids disjunction coverage of the standing class-separation detector

Bounded class-bound measurement task taken without an inbox assignment card (worker-036, node **A1**,
gate **G-AUDIT**, classes **AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-WCC-SCALAR-SPH**).
Worker measurement only: no gate verdict, no node completion, no canonical artifact modified.

## Question

`evaluation_rubric.yaml` defines **HF-02 `class_leakage` (critical)** with detector text
`unknown class_id | disjunction of class_ids | ...`, and its `frozen_classes` comment says
"Classes are not interchangeable and must never be disjoined in a statement."
The standing detector the A1 evidence route runs is `research_map/class_separation.py`
(called from `research_map/audit_evidence.py:104-119`, scored by
`runtime/bin/classsep_regression.py` against worker-07's 27-fixture corpus).

Does that detector report anything when a `class_ids` container holds two distinct frozen
classes — on synthetic isolates, and on the live L0 ledger rows that carry exactly that shape?

## Method

Read-only. Three public entry points were exercised per case, because callers differ:
`R1 findings()` (declaration mode), `R2 findings_for_map()` (`audit_evidence.py:110`),
`R3 findings_for_text()` (artifact-text scan, `audit_evidence.py:116`).
Controls must hold exactly or the checker exits 2 (fail-closed) and writes no report.
Each live row was additionally re-run with its `class_ids` container reduced to one token
(container-removal ablation): a finding that survives ablation is not attributable to disjunction.

Pinned snapshot (in `report.json`):

| input | sha256 prefix |
|---|---|
| `research_map/class_separation.py` | `c266dbceca87` |
| `runtime/bin/classsep_regression.py` | `9f1cf9c336be` |
| `evaluation_rubric.yaml` | `d748a9e3574e` |
| `ledger/theorems.jsonl` (live, rev4) | `a1674f094979` |
| `artifacts/worker-097/l0_rev3_review/snapshots/theorems.jsonl` (rev3) | `3e3d35531421` |
| `artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl` (pre-rev3) | `ce42d205e761` |
| worker-07 `results.json` | `d69ad58468be` |

## Result

Controls 6/6 PASS: merged single token, unknown token, composite prose, explicit prose merge
all fire; clean single class and split-prohibition prose stay silent.

| case | class_ids shape | R1 | R2 | R3 |
|---|---|---|---|---|
| X1 | `[C2, C0]` | silent | silent | silent |
| X2 | `[C0, C2]` | silent | silent | silent |
| X3 | `[WCC, C0]` | silent | silent | silent |
| X4 | `"C2,C0"` (comma string) | silent | silent | silent |
| X5 | `[C2, C0, WCC]` | silent | silent | silent |

Live L0 ledger (62 rows), on **all three pinned revisions** `a1674f094979` / `3e3d35531421` /
`ce42d205e761`: **8 rows** carry a `class_ids` list with ≥2 distinct frozen classes —
D-004(4), D-005(5), T-303(25), T-305(27), T-402(30), T-515(46), T-526(58), T-528(60).
Container-attributable findings: **0** on every revision. One row-route finding exists
(T-402 line 30, `regularity` prose "Between C0 and C2"); it survives container ablation and
is not attributable to disjunction. R3 and the whole-file route return **0** findings.

Worker-07 corpus: **0 of 27** fixtures carry a ≥2-known-class `class_ids` container, so the
recorded regression PASS (17 tp / 0 fn / 10 tn / 0 fp) cannot exercise the pattern the rubric
defines as critical HF-02.

A0 probe (off-label, raw): implemented HF-02 `artifacts/audit/audit_lib.py:140-185`
(`check_class_binding`) reads the singular `claim.class_id` plus statement text.
P1 (singular C2 + two-class `class_ids` list, statement not naming C0) → 1 violation, code HF-06 only.
P2 (ledger row shape, `class_ids` list only) → 1 violation, HF-02 for the absent singular `class_id`.
Neither produced the rubric condition "disjunction of class_ids".

## Findings (3 hard + 1 soft; each carries its own falsifier in `report.json`)

- **W036-DISJ-01 (hard)** — detector silent on X1–X5 through all three entry points.
- **W036-DISJ-02 (hard)** — 8 live rows, 0 container-attributable findings, stable on 3 pinned revisions.
- **W036-DISJ-03 (hard)** — the 27-fixture corpus that certifies the detector contains 0 instances of the pattern.
- **W036-DISJ-04 (soft)** — A0's implemented HF-02 does not implement its own rubric's "disjunction of class_ids" condition.

## Global falsifier

Re-run `python3 artifacts/worker-036/classsep_disj_coverage/check_disj_coverage.py --out report.json` on the
pinned hashes. FALSIFIED if (a) any control fails (exit 2); or (b) any X1–X5 isolate yields ≥1 non-SOFT
finding on any route; or (c) container ablation attributes ≥1 finding to a disjunctive `class_ids`
container on any pinned L0 revision, or a pinned revision no longer contains the 8 rows; or (d) the
worker-07 corpus is shown to contain a ≥2-known-class `class_ids` container; or (e) implemented HF-02
reports "disjunction of class_ids" on P1/P2.

## Reproduce

```bash
python3 artifacts/worker-036/classsep_disj_coverage/check_disj_coverage.py --selftest   # 6/6 controls
python3 artifacts/worker-036/classsep_disj_coverage/check_disj_coverage.py --out /tmp/report.json
# exit 1 = coverage gap confirmed; exit 2 = control failure (fail-closed)
```

## Interpretation limits

Binds only the pinned hashes above. The live ledger is a moving target (rev3 `3e3d3553` → rev4
`a1674f09` during this task); the two frozen copies make the result revision-robust, but a future
revision must be re-measured. This measures detector coverage, not whether any particular ledger row
should be reclassified; that disposition stays with the audit/literature leads.
