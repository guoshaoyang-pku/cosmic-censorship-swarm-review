# W069-LIFE05-REC12-REPAIR-COVERAGE-01

Independent, pre-registered sufficiency test of the authorized repair card
`astra-life05-evidence-binding-repair` (REC-12, controller Astra, 2026-09-12T00:48:41+08:00,
deadline 01:40, assignee astra-lead-formulation).

**Class-bound to:** AF-WCC-VAC-GEN (F1), AF-SCC-C2-VAC-GEN (F2a), AF-SCC-C0-VAC-GEN (F2b) — the
three classes the card moves. **Gate:** G-FORM. **Worker authority:** measurement and card
adjudication only; no canonical write, no gate verdict, no node status.

## Question

The card bounds the repair to exactly four items. At the rev12 pins, the blocking findings that
kept the three classes at *revise* were B1..B5 below. Which of them do those four items close, and
which will the rev29 re-review round (`astra-life05-verify-gform-r3`) reproduce?

## Answer (measured at FROZEN rev29, `artifacts/formulation/FROZEN.json#e1a8aaa394eb`)

**Verdict: `REPAIR_COVERAGE_INCOMPLETE` — 2 of 5 blocker classes closed, 3 open/ambiguous.**

| id | blocker | closure at rev29 | authorized item |
|---|---|---|---|
| B1 | declared `consistency_evidence_sha256` != measured evidence | **CLOSED** — all three schemas now declare `9e335e9b` == measured | item (2), executed |
| B5 | `taxonomy_cases.jsonl` rows bound to superseded F0 rev2 | **CLOSED** — 36/36 rows bind F0 rev5 `0abb9ed8` | item (1), executed |
| B2 | consistency evidence binds no digest of either compared tree | **OPEN** — a clean run of `check_taxonomy_consistency.py#de356d999ea3` reproduces the live 8-key document; it carries no `map_taxonomy_sha256`/`lead_contract_sha256`. The preserved `675a99d0` generation did carry both, so the predicate is satisfiable — but no item changes the checker, and item (2) pins the unpatched output | none |
| B3 | `schemas/af_scc_c0_vacuum.yaml.sha256` stale | **OPEN/AMBIGUOUS** — still records rev11 `1bb78ce9` while frozen rev29 C0 is `b2ab6acb`; not in the card artifact list and not in FROZEN rev29 `files` | none explicit |
| B4 | two-stage acceptance preflight (`run_acceptance.py`) | **OPEN** — faithful sandbox run exits **3 PREFLIGHT FAIL**: record base `1bb78ce9` vs frozen C0 `b2ab6acb`, and FROZEN rev29 itself pins the stale corpus (`semantic_escape_rebased.json#7e44de0e` carries base `1bb78ce9`). No item re-runs `measure_semantic_escape.py` | none |

**Consequence:** the two-stage acceptance criterion remains failing at the frozen rev29 bytes, so
the r3 round will reproduce HF-069R-2 / HF-069F2B-F07 on bytes it cannot judge. Recommended card
amendment: add (5) regenerate the acceptance corpus at the rev29 C0 hash and record the new
`base_sha256`, (6) refresh or retire the C0 sidecar, and record an explicit disposition for B2
(adopt a digest-emitting checker and pin its output, or accept B2 as a residual in the gate
criteria).

Note on B1/B2 coupling: item (2) is internally consistent only while the checker is unpatched.
Adopting a digest-emitting checker changes the evidence bytes, which makes item (2)'s named
target `9e335e9b` stale by construction — the two goals must be sequenced in one freeze.

## Falsifier

This coverage test is falsified if, at the rev29 pins: (a) any schema's declared
`consistency_evidence_sha256` != measured evidence; (b) the frozen evidence embeds the measured
sha256 of both compared trees and equals the declared pin; (c) the C0 sidecar equals the rev29 C0
hash or is explicitly out of scope; (d) `run_acceptance.py` reports `ACCEPTANCE: PASS` with
`record.base_sha256` == the rev29 C0 hash; or (e) a case row still binds `66bf917b`. Input drift
without a new freeze voids the binding, not the finding.

## Instrument and controls

`check_rec12_repair_coverage.py` — deterministic (double run at fixed inputs: identical report
sha256 `d87cceadd3ed`), stdlib+PyYAML, read-only on all canonical paths.

* C1 checker replay reproduces the live evidence bytes (`9e335e9b`) — PASS
* C2 one-token `family: "WCC"` mutant is discriminated (non-zero exit, different output) — PASS
* C3 acceptance preflight discriminates: fails on the live record, passes on a `base_sha256`-patched
  positive-control record — PASS
* C4 the preserved `675a99d0` generation demonstrably embeds both tree digests (so B2's predicate
  is not vacuous) — PASS

`report.json` carries every measurement, the card's canonical hash (`814bdb43c4cd`), all pinned
inputs and a start/end drift check (`STABLE`, no pinned input moved during the run).
`raw/` holds the sandbox replays (sandboxes are retained under `sandbox/`).

No canonical artifact was written. Prior credit: worker-086/094/034 (stale pin), worker-090
(H07/H07b), worker-041 (derived-output RCA), worker-092 (dropped binding fields), worker-016
(stale acceptance preflight), worker-030/096 (checker-patch drafts).
