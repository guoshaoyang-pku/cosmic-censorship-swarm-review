# W081-GFORM-F1-SUITE-MATERIALITY-01

**Worker:** worker-081 · **Class:** `AF-WCC-VAC-GEN` · **Node:** F1 · **Gate:** G-FORM · **Created:** 2026-09-12T01:04:33+08:00

## Task taken

F1's falsifier suite (`schemas/f1_falsifier_tests.jsonl`, 25 rows / 84 probes) binds the
**superseded** F1 rev12 hash `cce9c60146d6…` while the live canonical F1 schema is rev13
`d9cebb9404b2…` (FROZEN rev29 `815e08079aef…`). `worker-073` filed this as blocking hard
failure `F1-073-01` and prescribed either a rebind **or** "an explicit controller adjudication
that the declared semantics-preserving rev13 delta is immaterial for those probes".
`worker-029` measured the binding and probe mismatch counts. Nobody had enumerated the changed
leaves and tested whether the delta can move a probe verdict, with a positive control proving the
test is not vacuous. This card does exactly that, read-only.

## Result — `STALE_BINDING_PROBE_IMMATERIAL`

| measurement | value |
|---|---|
| pins stable start→end | yes (6/6) |
| rows / probes | 25 / 84 |
| binding | 25/25 rows `cce9c60146d6…`, `binding_frozen_revision=27` |
| changed leaf paths rev12→rev13 | 12 |
| **probe verdict flips rev12→rev13** | **0** |
| stored-vs-recomputed mismatches | 2 at rev12, 2 at rev13 (same set) |
| failing probes at rev13 | 2 — all in `F1-AMB-25` |
| rows all-probe-pass at rev13 | 24/25 |
| duplicate YAML mapping keys | 0 in both revisions |

**Adjudication.** (1) The stale binding is confirmed. (2) The rev12→rev13 delta is
**probe-immaterial**: all 12 changed leaves are either unreferenced by probes (8) or touched by
probes whose probed tokens survive the edit (4: `visibility.definition`,
`class_identity_variants[0].relation`, `f0_binding.binding_note`, and metadata); the 84-probe
verdict vector is identical at both revisions. So a pure binding restamp needs no probe-text
re-derivation, and worker-073's option (b) adjudication is defensible on this dimension.
(3) worker-073's three "materially affected" rows `F1-AMB-11/17/23` are **text-adjacent, not
verdict-affected**: their probes are sensitive to `visibility.definition` (control M1 moves 4 of
them), but the actual rev13 edit preserved every probed token, so 0/11 of their probes flip.
(4) **Separate blocker not fixed by any rebind:** `F1-AMB-25` carries two stale row expectations
that are false at *both* revisions — `declared_f0_sha256` expects `276009f4…` while the schema
declares the live F0 `0abb9ed8…`, and `binding_note` is expected to contain `astra-classscope-02`
which occurs nowhere in either revision. The suite is therefore **not green at the live pin**,
and a rebind alone does not make it green.

## Controls (anti-vacuity)

| control | mutation | probes moved |
|---|---|---|
| M1 positive | blank `visibility.definition` | 4 (F1-AMB-11/17/23) |
| M2 positive | restore F1-AMB-25 expected F0 hash | 1 (fail→pass) |
| M3 positive | delete `non_vacuity.condition` | 2 |
| M4 specificity | mutate unreferenced `authored_by` | 0 (required) |

M1–M3 prove the engine detects change; M4 proves it does not fire on unreferenced leaves.
Reproduce: `python3 artifacts/worker-081/f1_suite_materiality/measure_materiality.py`
(verdict `STALE_BINDING_PROBE_IMMATERIAL`, exit 0; exit 3 = pin drift).

## Prescriptions (worker-level, advisory)

1. Rebind the 25 rows to F1 `d9cebb9404b2` + FROZEN rev29 — mechanical on the measured dimension.
2. Or record the controller immateriality adjudication explicitly, citing this invariance evidence.
3. Repair `F1-AMB-25`'s two stale expectations or explicitly exclude that row from gate evidence.

## Falsifier

Re-run in an unchanged tree: any probe whose rev12 vs rev13 verdict differs; any pin measured
≠ recorded; a positive control moving 0 probes; the specificity control moving >0 probes; or a
changed-leaf count other than 12 falsifies this report.

**Authority:** no gate verdict, no node status, no `validation_status=passed`, no canonical byte
written. Evidence: `evidence.json#sha256:b392943c41f8`, tool `measure_materiality.py#sha256:44673c545d4e`,
report `report.json#sha256:5c40acfa98b3`.
