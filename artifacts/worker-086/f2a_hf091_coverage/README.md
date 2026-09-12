# W086-F2A-HF091-COVERAGE-01 — do the F2a accepts cover the disputed convention axes?

Worker `worker-086` · node `F2a` · class `AF-SCC-C2-VAC-GEN` · gate `G-FORM` · read-only on every
canonical path. Self-issued: no inbox card exists for this worker slot.

## One-line result

At the live pins, all three extension-predicate convention axes raised by `HF-091-02` are asymmetric
(F2b freezes them, F2a does not); the two live-hash F2a accepts — `worker-017` and `worker-072` — are
hash-valid full-schema verdicts, but neither accept's executed check script asserts any of the three
axes, and the frozen structural gate passes every one of the four axis mutants. **The accept pair does
not settle HF-091-02.**

## Live pins (measured before and after the run; 0 drift)

| path | sha256 (prefix) |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev13) | `e9a27996dfd3` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev13) | `b2ab6acb2bbe` |
| `research_map/formulation_taxonomy.yaml` (F0 canonical rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `artifacts/formulation/tools/check_class_schema.py` (frozen gate) | `000e09e46b2f` |

## Part A — the three axes at the live bytes

| axis | F2a | F2b | asymmetric |
|---|---|---|---|
| A1 manifold category of M' (smooth vs merely topological) | absent (`(c) M' is connected and time-orientable`; `extension_topology` says only `connected 4-manifold`) | frozen (`SMOOTH (C-infinity) connected 4-manifold`, twice) | yes |
| A2 iota regularity | absent (no `iota_regularity` key anywhere; no differentiability convention in `(a)`) | frozen at `non_vacuity.iota_regularity`: "the embedding iota is a C-infinity isometric embedding" | yes |
| A3 clause (f) interior requirement | absent (`(f) ... there exist q ... p in M' minus iota(M) with p in I^+(q; g')`) | frozen (`int(M' minus iota(M)) is non-empty AND ... p in int(...)`) | yes |

F0 does not discharge any axis: the C2 class contract fixes only the **metric** regularity
(`H4`: "extensions of regularity C2"), and the canonical taxonomy still records the
embedding-regularity gap as unresolved ("Definition subtlety (regularity of the embedding versus
regularity of the metric) is flagged unresolved and must be fixed by F2/L1", line 340). The F2b
interior repair note itself states its rationale is not regularity-specific.

## Part B1 — frozen-gate mutation probe

Null controls: live F2a, F2b, F1 all `pass`. Positive controls: conclusion token changed to the C0
token → `fail R11`; `class_id` changed to the sibling → `fail R02,R06,R11,R18,R19,R31`.

| mutant | axis | gate verdict |
|---|---|---|
| `m1` M' named a topological 4-manifold | A1 | **pass** (blind) |
| `m1b` M' named SMOOTH (repair-like) | A1 | pass (indifferent) |
| `m2` `iota_regularity` added as merely continuous | A2 | **pass** (indifferent) |
| `m3` interior requirement added to (f) | A3 | pass (indifferent) |
| `m3b` future-witness content removed from (f) | A3 | **pass** (blind) |
| `m6` `must_not_conflate` emptied | adjacent | **pass** (blind datum) |
| `m7` clause marker `(f)` renamed to `(g)` | A3 marker | **pass** (blind datum) |

The frozen gate therefore cannot certify any of the three axes; a gate `PASS` is not evidence that
the C2 extension predicate is frozen.

## Part B2 — accept coverage

Both accepts declare `counts_as_full_schema_verdict: true` and bind
`reviewed_sha256 = e9a27996dfd3…` (the measured F2a bytes), so they are procedurally valid at the
live hash. Their executed check scripts, however, contain no assertion on A1, A2 or A3:

- `worker-072` `C10_EXTENSION_PREDICATE` asserts only `frozen_regularity == C2`,
  `frozen_equation_concept == classical_ricci`, `frozen_direction == future`, and that the
  definition text contains all six clause markers. It also covers the metric-regularity axis
  (control K2), so the coverage classifier is not blanket-negative.
- `worker-017`'s script loads `extension_predicate` but asserts nothing about the three axes.

## Controls

K1 F2b positive (all three axes found) · K2 covered-axis control (072 asserts the metric-regularity
value) · K3 determinism (two passes, equal digest) · K4 pin stability (0/12 pins moved) ·
K5 null controls pass · K6 positive controls fire. All PASS; `run_valid: true`.

## Run history

Pass 0 was invalid and is recorded in `report.json.run_history`: the clause extractor was
last-wins and captured F2b's parenthetical "clause (f) was escapable" as clause (f); the
`iota_regularity` lookup was top-level-only while F2b nests it under `non_vacuity`; K2 was
over-strict; and an empty-`must_not_conflate` mutant was wrongly used as a positive control (the
frozen gate does not catch it). The pre-registered hypotheses and falsifiers were not changed.

## Authority

Worker measurement only. No canonical file was written, no node status, no `validation_status=passed`
and no gate verdict is claimed. This report measures document bytes and the frozen gate's behaviour;
it makes no mathematics claim and does not adjudicate `HF-091-02`.

## Next falsifier

Re-run at the next F2a revision: H1 is refuted by a measured symmetric axis at the new bytes; H2 by
an axis-specific assertion in an accept's executed checks; H3 by an axis mutant that fails the frozen
gate; H4 by a live-hash accept whose declared sha256 differs from the measured file.

## Artifacts

- `PREREGISTRATION.json` — pins, hypotheses, controls, falsifiers, written before the run.
- `verify_hf091_coverage.py` — deterministic probe (stdlib + PyYAML only).
- `report.json` — full machine-readable result (all checks, hits, quoted lines).
- `sandbox/` — mutated copies only; no canonical file.
