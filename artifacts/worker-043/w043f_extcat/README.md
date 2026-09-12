# W043F — F2a extension-category adjudication (worker-043)

**Task** `W043F-F2A-EXTCAT-ADJUDICATION-01` · **gate** G-FORM · **nodes** F2a / F1 / F2b ·
**classes** AF-SCC-C2-VAC-GEN (F2a), AF-SCC-C0-VAC-GEN (F2b), AF-WCC-VAC-GEN (F1)

## What was asked

At the FROZEN rev29 pins, F2a (`schemas/af_scc_c2_vacuum.yaml`, `e9a27996dfd3`) omits the
`SMOOTH (C-infinity) connected 4-manifold` pin and any `iota_regularity` key that the C0 sibling
F2b (`schemas/af_scc_c0_vacuum.yaml`, `b2ab6acb2bbe`) freezes. worker-028 (HF-028R-01) and
worker-047 (HF-047-01), originating from worker-091 (HF-091-02), score the omission **blocking**
at the same hash where worker-017, worker-072 and worker-075 **accept**. G-FORM needs independent
verdicts per class, so the severity of this item decides whether an F2a accept at `e9a27996dfd3`
can bind. No worker had adjudicated the item's materiality.

## Verdict

| axis | result |
|---|---|
| Text asymmetry | **reproduced** — F2a has no category token and no `iota_regularity` key; F2b has both |
| Manifold-category half | **redundant_derived** — clause (d) pins the metric to *exactly C2*; manifold + C^k metric (k≥1) determines a unique compatible smooth structure, so the explicit token adds no constraint to F2a |
| iota-regularity half | **unstated_convention (non-blocking)** — clause (a) is byte-identical to F2b's and its tensor equation already excludes a merely topological embedding; the residual C1/C2/C∞ convention is unstated but no differentiating witness was exhibited |
| Normativity | **not a rule failure** — rule_spec R01–R16 has no category/iota requirement; the canonical structural gate `check_class_schema.py` (R01–R31) has **0** occurrences of `iota`, `manifold`, `category` |
| Recommended severity | **downgrade to minor documentation**; this item alone does not defeat an F2a accept at the pinned hash |

The asymmetry tracks the mathematics rather than an oversight: F2b *needs* its explicit pin
because its metric is only **C0** (a C0 atlas determines no smooth structure), and F2b clause (c)
records exactly that accepted rationale (worker-16 F2b-16-03). F2a's metric is exactly **C2**, so
the category is derived. Control **C1** isolates the boundary: flipping F2a clause (d)
`C2 -> continuous` flips the derived category to `UNDETERMINED_C0_METRIC`, while the live F2a
stays `DETERMINED_SMOOTH`.

If the lead prefers parity (Option B in the report), a one-sentence clarification of clause (c)
plus one `iota_regularity` key closes it with **annotation-only** content effect; because that
re-cuts the F2a hash and FROZEN, it belongs to the next authorized revision, not to a worker.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-043/w043f_extcat/check_extcat.py \
  --scratch tmp/w043f_scratch \
  --out tmp/w043f_scratch/extcat_raw.json
# exit 0, hard_failed == [], drift == [], controls 4/4
```

16 checks, 4 pre-registered mutation controls, 12 hash pins measured at entry and exit.
Last run `2026-09-12T01:03:55+08:00`; raw output frozen at
`raw/extcat_raw.json` sha256 `5eb08e6411223e7721c9a2f55f73f5f22fbb563acde590541c13e619b5a31f62`.

## Falsifier

Void/falsified if (a) any of the 12 pinned paths moves from its recorded sha256; (b) F2a is shown
to contain a category token or `iota_regularity` key at the measured hash; (c) a differentiating
witness triple is exhibited (a triple satisfying F2a's literal clauses and failing the sibling's
frozen C∞-iota convention); (d) the smoothing-theorem step is shown inapplicable to an exactly-C2
Lorentzian metric; or (e) a rule or r3 criterion requiring the explicit pin is produced.

## Authority

Worker evidence only. This report cannot set a gate verdict, node status or `validation_status`,
and it is not one of the two binding independent verdicts per class that G-FORM requires. It
adjudicates the **severity of an existing reviewer finding**, not the mathematical content of
AF-SCC-C2-VAC-GEN. Read-only task: **no canonical byte was modified**; every mutation ran on
in-memory copies or under `tmp/w043f_scratch/`.
