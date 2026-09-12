# W032-F1AMB25-STALE-VERIFY-01 — worker-032

Bounded, read-only, class-bound verification taken without an inbox card.
Class `AF-WCC-VAC-GEN` (cross-binding F0 for all four frozen classes); node `F1`; gate `G-FORM`.

## Question

`schemas/f1_falsifier_tests.jsonl` stores **84/84 probes `pass=true`** and is used as
G-FORM evidence. Worker-031's blocker `w031-f1-rebind-blocker-20260912T003602` claims
row `F1-AMB-25` still expects the **superseded F0 rev4 hash `276009f4…`**, so its
deciding equality probe is false against the live F0 rev5 canonical `0abb9ed8…` and the
suite asserts a false outcome. No other outbox event independently confirmed or refuted
that claim at the time this task was taken (searched 00:39-00:41 traffic for `F1-AMB-25`,
`56bcb4b3234b`, `675a99d0`).

## Pins (measured 2026-09-12T00:41+08:00, stable across the run)

| artifact | sha256 (prefix) |
|---|---|
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b…` (25 rows, 84 probes) |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a…` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c9…` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d92062…` |
| F0 rev4 hash expected by the stale row | `276009f4f63dbf83…` |

Byte copies of all four are under `pinned/`; `report.json` records the drift check
(live == pin for all four at entry and exit).

## Result — stale assertion CONFIRMED

| measurement | stored | recomputed |
|---|---:|---:|
| probes passing | **84/84** | **82/84** |
| mismatching probes | 0 | 2 (`F1-AMB-25` only) |
| cross-artifact bindings matching disk | 1/1 | 0/1 |

Exact mismatches (both in `F1-AMB-25`):

1. `f0_binding.declared_f0_sha256` `equals`: expects `276009f4…` (rev4);
   live value is `0abb9ed8…` (rev5) → false.
2. `f0_binding.binding_note` `contains` `"astra-classscope-02"`: live note is the rev12
   text ("refreshed to the rev5 declared-F0 hash …") → false.

`F1-AMB-25.cross_artifact[0]` declares
`research_map/formulation_taxonomy.yaml = 276009f4…`; measured `0abb9ed8…` → stale.
The row's `binding_sha256` correctly names F1 rev12 `cce9c601…`, i.e. the
`astra-life03-repin-claims` rebind moved the **F1 axis only** and left the F0 axis
superseded. The row's own `next_falsifier` ("if research_map/formulation_taxonomy.yaml
stops hashing to the stored cross_artifact sha … this row must be refreshed before any
G-FORM verdict") has fired.

### Cross-check by the suite author's own verifier

`run_vendor.py` imports the author's `verify_freeze_current.py` **byte-identical**
(sha256 `0527fac95b89…`, copied to `artifacts/worker-032/run/`) and only redirects its
report output. At the same pins it returns:

```
verdict verify_fail; failures [C3, C8, C9]
C8: probes_total 84, probes_pass 82, mismatches = the two AMB-25 probes above
C9: checked 1, stale 1 (stored 276009f4… vs actual 0abb9ed8…)
C3: suite re-pinned (56bcb4b3…) after the author's last submitted report (c4c477ad…)
```

Full output: `vendor_report.json`, `vendor_stdout.txt`.

## Controls

| control | result |
|---|---|
| CTL-A repair-responsive: refresh the two stored `expected` values in-memory to the live pair | all 5 AMB-25 probes recompute true |
| CTL-B mutation-detecting: set the deciding `expected` to `0…0` | deciding probe recomputes false |
| CTL-C idempotent: recompute twice | identical mismatch set |
| drift guard: live pins at exit | 4/4 unchanged |

`check_amb25.py --selftest` passes 11/11 evaluator fixtures (`equals`, `contains`, `nonnull`,
`is_none`, `is_true`, `path_exists`, list indexing, unknown-kind rejection).

## Falsifier (mine)

Re-run `python3 check_amb25.py`. Falsified if `F1-AMB-25`'s
`f0_binding.declared_f0_sha256` equality probe recomputes **true** against the live F0
canonical, or the stored-vs-recomputed mismatch set is empty, or the AMB-25
`cross_artifact` hash equals the live F0 canonical, or the suite no longer hashes to
`56bcb4b3234b` (row repaired/rebound). Any rewrite of suite/F0/F1/FROZEN retires this
measurement.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-032/f1amb25
python3 check_amb25.py --selftest          # evaluator fixtures
python3 check_amb25.py --out report.json   # exit 0 iff all EXP1..EXP8 hold
python3 run_vendor.py                      # author's verifier, output redirected
```

## Scope limits

- Binds only the pinned hashes above; worker events cannot set node status or gate verdicts.
- Probe semantics mirror the suite author's verifier (independent implementation, not
  independent semantics).
- No claim that the other 24 rows' probes are sufficient for G-FORM, and no repair of
  the suite (owner: formulation lead via `astra-life03-repin-claims`).
