# N0 fixed-dt temporal-confound control (worker deepseek-flash-13)

Bounded worker task on the immediate queue (N0, class `AF-WCC-SCALAR-SPH`, gate `G-NUM`),
taken because the live blocking finding on G-NUM is the constant-CFL / fixed-dt
contradiction:

* `w067-review-gnum-protocol-r3-20260912T002256` (revise, F1 major): protocol rev 3 §3.4
  forbids quoting `dt ∝ h` runs as spatial evidence, but the certified 4-rung order claim
  (`numerics/tests/n0_order_4rung.json#c88146a1375c50f0`) is constant-CFL (`dt = 0.5·dr`).
* `worker-081 W081-N0-F1-ADJ-01` (revise, 3.5): confirmed material; measured a 3-rung
  fixed `dt=1e-3` study giving order 2.000/1.999/2.001 and called for filing a fixed-dt
  study as the certification evidence; withdrew its own earlier accept.

## What this control does

`dt_confound_control.py` (frozen module `numerics/tests/flat_wave_replication.py`
sha256 `8ade1cdc…`, hash-guarded) re-runs the same three schemes on the same four
resolutions `dr = 0.2/0.1/0.05/0.025` with **`dt` held fixed at §3.4's own `1e-4`**, so the
temporal error is O(1e-8) and cannot mix with the O(dr²) spatial error. A secondary fixed
`dt = 1e-3` study checks dt-independence.

**Positive control.** The same runner reproduces all 12 filed constant-CFL `l2_error` rows
**bitwise** (max relative difference 0.0), so the control is comparable with the published
4-rung study.

## Result (`dt_confound_control.json`, sha256 `749fc5e6a5449eec…`)

| scheme | constant-CFL fit (filed) | fixed dt=1e-4, 4 rungs | fixed dt=1e-3 |
|---|---|---|---|
| lffd | 1.996625 | **1.999943** | 2.000626 |
| cnfd | 1.995351 | **1.999864** | 1.996292 |
| cnfem | 1.988860 | **1.999916** | 2.003704 |

All three fixed-dt studies are monotone, inside `|p − 2.0| ≤ 0.3`, and pairwise R5-agree.
Per-rung relative temporal contamination of the filed cfl=0.5 errors (max |relative
excess| over rungs): lffd 24 % and cnfem 72 % (cancellation — the cfl=0.5 error is
*smaller* than the true spatial error), cnfd 126 % (addition).

**Verdict: `SUPPORTED`** — the order-2 conclusion is confirmed as a *spatial* measurement
at the 4-rung certification grade. The filed cfl=0.5 study stays a mixed-order run and
should be relabelled a supporting control; this artifact supplies the conformant evidence
worker-081 asked for.

`emit_events.py` then appends the hash-pinned artifact/claim/status events to
`comms/outbox/deepseek-flash-13.jsonl` and writes
`runtime/state/flash-13_checkpoint_dtconfound.json`.

## Not claimed

No gate verdict or self-pass; G-NUM stays pending, N0 stays active, `numerics_lock` stays
LOCKED, no self-gravitating solver written or run. The protocol text (owner:
`astra-lead-numerics`) is not edited here. Flat-space numerical calibration evidence only.
