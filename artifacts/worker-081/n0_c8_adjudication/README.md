# W081-N0-F1-ADJ-01 — adjudication of the worker-067 F1 finding on G-NUM/C8

Question: *worker-067* (`comms/outbox/worker-067.jsonl`, `w067-review-gnum-protocol-r3-…`,
00:22:56) claims F1 (major, blocks accept): protocol §3.4 forbids `dt ∝ h` runs as spatial
evidence, yet the certified order claim uses exactly those constant-CFL runs. Two accept
verdicts (worker-081 `W081-N0-C8-01`, lead-audit `reviews/G-NUM-protocol-review.json`) and
one revise verdict sat at the same protocol hash `1e6cdf04d7a2`. This directory settles it
by measurement, not by text.

**Protocol reviewed:** `numerics/CONVERGENCE_PROTOCOL.md`
sha256 `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` (rev 3).
**Class:** `AF-WCC-SCALAR-SPH` (calibration sub-case). **Node:** N0. **Gate:** G-NUM.

## Verdict (worker-level; no gate verdict, no node completion)

**F1 is CONFIRMED and it is material, not text-only. worker-067's disposition
("no number changes — scope the text in rev 4") is REFUTED as stated.**

Measured facts (all in `adjudication.json`, reproducible with `adjudicate_f1.py`, 47 s):

| check | result |
|---|---|
| §3.4 clauses present at review hash | fixed `dt=1e-4` spatial + "`dt ∝ h` … never quoted as spatial" — both true |
| certified claim advertises `cfl=0.5` | true (`n0_gate_proposal.json#58a175b52fbe`) |
| all 12 certified 4-rung rows have `dt = 0.5·dr` | true (bitwise; E1 `dt=0.025` reruns reproduce the filed errors **bitwise**) |
| any filed study with constant `dt ≤ 1e-3` | **none** — the protocol's own spatial methodology was never executed on the filed evidence |
| temporal subdominance at cfl=0.5, fixed `dr=0.05`, dt halved twice | **lffd 22.4 %, cnfd 41.8 %, cnfem 143.4 %** error change — far above the canonical 2 % rule |
| direction of change | lffd `3.20e-4 → 4.10e-4`, cnfem `1.17e-4 → 3.83e-4`: the error **grows** toward the true spatial error ⇒ cancellation between temporal and spatial error at cfl=0.5 |
| cfl=0.5 error ÷ fixed-`dt=1e-4` error at `dr=0.1` | lffd 0.77×, cnfd 2.26×, cnfem 0.28× — the filed study does not measure the right magnitude |
| protocol-style fixed `dt=1e-3` study, `dr=0.2/0.1/0.05` | order **2.000 / 1.999 / 2.001** (lffd / cnfd / cnfem) |

So the order-2 *conclusion* is recoverable and is corroborated by a §3.4-compliant study;
what fails is the *filed evidence*: the certified "spatial order 2" is a mixed
spatial–temporal order measured with cancellation. This also withdraws worker-081's own
`W081-N0-C8-01` accept at the same hash.

## Remedy (for lead-numerics / lead-audit / controller)

1. File the fixed-`dt` study as the **order-certification** evidence (extend E2 with
   `dr=0.025`, and/or `dt=1e-4` — E3: 60 000 steps, lffd 0.6 s, cnfd 17 s, cnfem 16 s per rung).
2. Keep the cfl=0.5 4-rung study as a labelled **mixed-order supporting control**.
3. Amend §3.4 in rev 4 to name the fixed-`dt` study as the admissible spatial measurement and
   to require the fixed-`dr` dt-refinement control for any quoted constant-CFL run.

## Files

| file | role | sha256 |
|---|---|---|
| `adjudicate_f1.py` | harness: pinned hashes, text checks, E1–E3, reproduction, verdict | see `checkpoint.json` |
| `adjudication.json` | full machine-readable result + verdict + falsifier | see `checkpoint.json` |
| `checkpoint.json` | worker checkpoint: measured input/output hashes, task state | see below |
| `README.md` | this file | see `checkpoint.json` |

## Falsifier (binds the verdict)

Re-measure `numerics/CONVERGENCE_PROTOCOL.md`: if its sha256 is not `1e6cdf04d7a24313`, this
adjudication does not bind. It is falsified if a filed study with constant `dt ≤ 1e-3` across
≥ 3 rungs exists; if a rerun of `adjudicate_f1.py` at frozen module hash `8ade1cdc163ea420`
finds the E1 max relative change below the 2 % rule; or if
`numerics/tests/flat_wave_replication.py` no longer hashes `8ade1cdc163ea420`.

**Not claimed:** no gate verdict, no node completion, N0 stays active and `numerics_lock`
stays LOCKED; no physics claim; no claim that the measured order is wrong — the question was
whether the *label "spatial"* is established by the filed evidence. Worker evidence only.
