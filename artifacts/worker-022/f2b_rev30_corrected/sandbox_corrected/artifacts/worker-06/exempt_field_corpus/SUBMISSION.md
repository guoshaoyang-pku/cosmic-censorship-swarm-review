# worker-06 submission — FORM-EXEMPT-09 (bounded run)

**Task taken (one class-bound task).** Successor to `FORM-HELDOUT-07`, following the formulation
lead's stated next step: build and measure a held-out corpus of class-contract leaks hidden in the
**exempt explanatory fields** that neither acceptance stage scans by design
(`comms/inbox/worker-06.jsonl:7`). Node `A1`, gate `G-CLASSBIND`; classes
`AF-SCC-C0-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-WCC-VAC-GEN`.

**Status.** Measurement complete, corpus VALID, results reported as-is. No node completion, no
theorem, no physics result; worker cannot set `done`/`passed`.

## Headline

On the frozen canonical schemas (FROZEN rev18, verified 0 drift), **18/18** pre-registered mutants
carrying a frozen-invariant leak in an exempt/unscanned field escape **both** stages
(structural `000e09e46b2fb4ab`, semantic `c79d8ab8440ac673`); all 10 controls are accepted, so the
corpus is not format-dominated. A post-hoc, hash-bound relocation control shows 11/14 sentences are
caught with the expected rule when moved into a scanned field (genuine field-exemption escapes),
while 3 are not caught even there (all-field gate gaps: matter-in-VAC token absent from R12, transfer
truth-table prose unchecked by R28, R15 regex narrower than its spec).

## Artifacts (all under `artifacts/worker-06/exempt_field_corpus/`)

| artifact | sha256 | role |
|---|---|---|
| `manifest.json` | `0627216b6b276f80…` | pre-registered corpus (18 mutants / 14 families / 7 controls) |
| `report.json` | `8af6bb5a3ba15864…` | two-stage measurement, aggregates, escape families |
| `relocation_manifest.json` | `4461a18a03a1bf4b…` | post-hoc criterion-control registration |
| `relocation_report.json` | `60a57bdbd447b6c3…` | 11 confirmed / 3 gate gaps / 0 criterion failures |
| `classification.json` | `c5236a877374cc24…` | 14 field-exemption + 3 all-field + 1 prose-only |
| `FINDINGS.md` | see checkpoint | full write-up, family table, falsifiers, limits |
| `make_corpus.py` / `run_corpus.py` / `relocation_controls.py` | see checkpoint | reproducible generators/runners |

Gate implementation hashes and fixture-level hashes are recorded in `report.json` and
`manifest.json` respectively. The main corpus manifest/report were frozen before measurement; the
relocation control is explicitly post-hoc and did not modify them.

## Events emitted (comms/outbox/worker-06.jsonl)

- `artifact` × 6 (manifest, report, relocation report, classification, FINDINGS, toolchain)
- `status` (`w06-20260912T0045-exempt09-status`)
- `claim` (`w06-20260912T0045-exempt09-claim`, `conclusion_type: formal_model`)

Each event carries `event_id`, `created_at`, `actor`, evidence refs as `path#sha256-prefix`, and a
falsifier. Checkpoint: `runtime/state/w06_checkpoint_5.json` (+ append to
`runtime/state/w06_checkpoints.jsonl`).

## Falsifiers / next falsifier

Any mutant shown not to violate a frozen invariant, or any control rejected by either stage,
invalidates the corresponding part of this measurement. Highest-value next step: extend the
structural gate to scan explanatory prose with polarity awareness (tagged exemptions), add the missing
matter/asymptotic token, widen R15 to the spec wording, and add a prose transfer check — then
re-measure on a **fresh** corpus (never this one).
