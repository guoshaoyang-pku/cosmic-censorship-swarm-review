# worker-005 — F2 re-bind / class-separation audit (independent)

- **Node** F2 · **classes** `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · **gate** G-FORM
- **Measured at** 2026-09-12T00:30:52+08:00
- **Task** independent re-bind of `schemas/af_scc_regularities.yaml` to the live component pins,
  with a from-scratch separation/leakage checker consuming the worker-06 rule set
  (assignment `astra-adj1-05-assignment`).
- **Checker** `check_f2_rebind.py` — selftest PASS: null control clean, 6/6 planted mutants caught.
  Fixtures 10/10 (8 negatives rejected, 2 positives accepted, both null controls pass).

## Measured pins

| artifact | sha256 |
|---|---|
| `schemas/af_scc_regularities.yaml` | `94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4` |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |

The aggregator's declared component pins equal the disk hashes at the measured instant, so the
index is **re-bound**, not drifted. Both components pass the frozen binding gate
`artifacts/formulation/tools/check_class_schema.py` (FORM-RULE-SPEC v1.1, R01–R16, verdict pass,
no failed rules). The author lint `artifacts/worker-05/check_f2_integration.py` was re-run at the
same instant and agrees: overall pass at `94562101a816`.

## Separation result — PASS

- A2/A4: exactly the two SCC class ids, once each, in separate component entries; no joined
  class-id string anywhere in the index text.
- A5: no composite regularity token in the index (the index may not even mention one).
- A6: no `conclusion`/`conclusion_type` object and no extension statement in the index.
- A7: no anchors, aliases or merge keys.
- B3: component conclusions non-empty, distinct, family-separated; no cross-family token outside a
  relation/prohibition field.
- B4: frozen gate R13 passes on both components; the raw `C0 or C2` occurrence lives only in
  prohibition/comment text (a mention, not a use).

Disposition on class semantics: **N** — no class merge, no conclusion inflation.

## Evidence hygiene — FAIL (orthogonal to separation)

| id | finding | evidence |
|---|---|---|
| H1-duplicate-keys (index) | `revised_at` appears **×4** as a mapping key; YAML last-wins silently selects `2026-09-12T00:40:00+08:00` | `schemas/af_scc_regularities.yaml:11-14` |
| H2-future-timestamps (index) | `revised_at: 2026-09-12T00:40:00+08:00` is later than the measured instant (00:30:52) | `schemas/af_scc_regularities.yaml:14` |
| H1-duplicate-keys (components) | `revised_at` appears **×8** in each of C2/C0 | `schemas/af_scc_c2_vacuum.yaml`, `schemas/af_scc_c0_vacuum.yaml` |

These are the same defect class worker-005 reported for F1/F2a/F2b at 00:26
(`HF-W005-01/02/03`), now confirmed on the F2 index itself. They do not show a class merge; they
mean the index's own revision annotation cannot be used as evidence for "which revision was
measured" — the declared revision is a silent last-wins value, one of whose alternatives is in the
future. Repair owner: lead-formulation (owner of record) / `deepseek-flash-05` (author). Repair:
delete the duplicate `revised_at` keys, keep one true value, correct future dates, re-run
`check_f2_rebind.py --report`; H1/H2 must flip to pass or the blocker stands.

## Falsifier

Re-measure the pins in `report.json`: a component hash differing from its aggregator pin, a joined
class-id or composite regularity token in the index, a fixture labelled `fail` accepted (or `pass`
rejected), or the hygiene findings absent from a repaired revision each supersede or refute the
corresponding verdict here. A repaired aggregator with deduplicated, non-future timestamps
falsifies H1/H2 specifically.

## Authority note

This is a worker measurement. Worker events cannot set `status=done`,
`validation_status=passed`, or a gate verdict. The re-bind and hygiene results await controller
ingest.
