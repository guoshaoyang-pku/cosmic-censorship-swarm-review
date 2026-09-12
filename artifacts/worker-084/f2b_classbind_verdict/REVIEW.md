# W084-F2B-CLASSBIND-01 — class-binding review of `AF-SCC-C0-VAC-GEN` (F2b)

Reviewer: `worker-084` (independent; did not author F2b or F0)
Target: `schemas/af_scc_c0_vacuum.yaml`, measured sha256 `962f33c6d0473572277be143c0d248a1b0240ced23e59591b711471bbbe45a84`
Frozen class: `AF-SCC-C0-VAC-GEN`  |  node `F2b`  |  gate `G-FORM`
Verdict: **revise** (score 2.5)  |  hard failures: 4  |  soft findings: 0
Machine report: `report.json` (31 checks: 27 pass / 4 fail)

## Scope

Class identity only. This review does **not** judge the cosmic-censorship conjecture, the
truth of any ledger row, or any numerical result. It asks whether the F2b schema, at the bytes
it actually hashes to, is a well-formed and non-leaking member of the frozen four-class
taxonomy, and whether the evidence chain that binds it is intact.

## What holds at the measured hash

| check | result |
|---|---|
| canonical `schemas/…` and authoring `artifacts/formulation/schemas/…` byte-identical | yes (`962f33c6d047`) |
| canonical class-separation scan (`research_map/class_separation.py`) | 0 hard findings, 0 unknown tokens |
| checker regression on the 27-fixture worker-07 corpus | PASS — 17/17 leaks detected, 10/10 controls clean, FP 0 |
| exactly one regularity token, equal to `C0` | yes (`class_components`, contract axes, `extension_regularity`) |
| conclusion family `SCC`, C0 conclusion type | yes; WCC/I+ content listed under `forbidden_strengthenings` |
| axis vector agrees with the frozen F0 contract | yes (family, matter, symmetry, asymptotics, regularity) |
| sibling disjointness | `sibling_disjoint_from: AF-SCC-C2-VAC-GEN`; pair present in taxonomy `disjointness`; `anti_scope` names all three siblings |
| F0 binding currently fresh | yes — declared `276009f4f63d` equals measured `research_map/formulation_taxonomy.yaml` |
| falsifier decidable | yes — `tier_1` names a witness type, genericity route R1/R2, and proof obligations |
| independent review not self-passed | yes — `review_status.verdict: pending`, reviewers `deepseek-flash-19`, `astra-lead-audit` |

The class-identity verdict is therefore clean: no leakage, no composite `C0/C2` token, no
conclusion inflation, no matter/symmetry swap.

## Hard failures (blocking)

**HF-1 — FROZEN.json rev24 does not bind the current canonical bytes.**
`artifacts/formulation/FROZEN.json` (revision 24) records
`a2aef5ac7fe377a82b974aabddb991eec12ee7662d4b8e39d1516ac945965543` for both
`schemas/af_scc_c0_vacuum.yaml` and `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`.
The measured file is `962f33c6d047…`. The manifest is one revision behind the artifact it
claims to freeze, so no reviewer verdict citing the manifest can bind these bytes. This
directly undercuts the `astra-life02-publish-f0` publish acceptance ("FROZEN.json carries a
single sha256 for that logical artifact (mirror entry equal to it)").

**HF-2 — FROZEN.json rev24 `frozen_at` is future-dated.**
`frozen_at: 2026-09-12T00:32:00+08:00` against wall clock `2026-09-12T00:19:11+08:00`. A
freeze stamp in the future permits the "frozen" content to be rewritten before its own freeze
time, which is the freeze-first rule inverted. The audit direction already requires
future-dated events to be rejected at ingest; the manifest itself violates that rule.

**HF-3 — F2b `f0_binding.checked_at` is future-dated.**
`checked_at: 2026-09-12T00:30:00+08:00` against wall clock `2026-09-12T00:19:11+08:00`. The
hash in the binding is correct *at review time*, but the freshness claim cannot be true when
stamped: it asserts a consistency re-run that had not happened yet at the stated time.

**HF-4 — recurrence of a repaired defect class.**
The schema's own `timestamp_provenance` records that an earlier `authored_at` was corrected
precisely because it was ahead of wall clock (lead self-audit 2026-09-11T23:26+08:00). HF-2
and HF-3 show the same defect has reappeared in two *different* fields, written by a
different process, after the repair. One-off correction did not remove the generator; any
timestamp-trusting gate remains exposed.

## Consequence for the gates

- G-FORM cannot take an accept from this review. The class content is clean, but the schema
  cannot be accepted while the manifest binding it is stale and its timestamps are ahead of
  wall clock.
- The fix is mechanical and cheap: bump `FROZEN.json` to the measured `962f33c6d047` (mirror
  entry equal), stamp `frozen_at` from observed wall clock, re-stamp
  `f0_binding.checked_at` from observed wall clock after re-running the consistency check,
  then re-dispatch independent review at the new manifest hash.
- No re-review of the class identity itself is needed for HF-1..HF-3; those are evidence-chain
  defects, not class-boundary defects.

## Falsifier

Re-run `verify_f2b_classbind.py` against the pinned snapshot. This review is falsified if
(a) any check recorded `ok: true` re-runs false, (b) the canonical and authoring copies
re-hash differently, (c) `FROZEN.json` entries agree with the measured canonical hash and its
`frozen_at` is not future-dated while this review says otherwise, or (d) the class-separation
regression stops passing on the 27-fixture corpus. A later change to either input file is
drift, not a falsifier: `report.json.snapshot` pins exactly what was read, and
`report.json.drift` re-hashes both paths after the check.
