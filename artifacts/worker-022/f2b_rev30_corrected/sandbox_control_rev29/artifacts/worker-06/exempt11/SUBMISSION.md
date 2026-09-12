# FORM-PROBE-11 / EXEMPT-SURFACE-11 — submission (worker-06)

**One bounded, class-bound task.** Node `A1`, gate `G-CLASSBIND` (calibration evidence routed to
`G-AUDIT` per `astra-w06-01`), classes `AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN`.
Pins: FROZEN **rev28** (2026-09-12T00:35:08+08:00), structural gate `000e09e46b2f`, rule_spec
`40f9bb9e657b`, KEY_MANIFEST `014e2d301978`, canonical schemas `cce9c60146d6` / `5476a3f2c6bc` /
`55d0a1ea9bda`.

## Lineage and what is new

This is the **re-measurement FORM-EXEMPT-09 itself required**. That predecessor measured 18/18 union
escape at FROZEN **rev18** and was invalidated for the current revision by freeze drift; it stated
that a re-measurement on the new disk hashes requires a **new** pre-registered corpus
(`artifacts/worker-06/exempt_field_corpus/`, manifest `0627216b6b27`, report `8af6bb5a3ba1`).

This run supplies exactly that at FROZEN rev28, plus two things the predecessor did not have:
(a) a mechanical leaf-level **surface inventory** (~95 % of canonical string leaves outside the
family-token scan), and (b) a **false-positive-calibrated** candidate rule with measured rejection of
the broad variants. The headline replicates across revisions: union escape **1.0000 at rev18 and
1.0000 at rev28** on independently built corpora.

## Question

The canonical gate's own docstring lists the blind spot: *"lexical leakage scan covers
ASSERTIVE_PATHS only; a semantic leak expressed purely in un-scanned prose fields passes."* The
formulation lead's held-out acknowledgement named the next corpus: *"prose leaks in the exempt
explanatory fields, which neither stage scans by design."* This run measures exactly that surface.

## Method (pre-registered, fail-closed)

- 31 fixtures = 3 canonical pass controls + 3 legitimate-negative controls + 3 sensitivity
  controls + **22 candidate mutants** (`m01`–`m22`).
- Every mutant is **byte-level single-leaf surgery** on a canonical schema; a deep diff of the
  parsed docs is asserted to change exactly the declared target path. The operative/assertive
  statement blocks stay canonical.
- Three declared surface classes: **S1** `EXEMPT_KEY` subtree, **S2** non-exempt declarative field
  outside `ASSERTIVE_PATHS`, **S3** revision/provenance/status metadata.
- `manifest.json` hashed **before** the run (`98e7289a2cfc…`), fixtures re-checked against the
  manifest, all pins re-measured **after** the run. Any drift voids the corpus.
- Stages: A = canonical `check_class_schema.py` (R01–R31); B = frozen worker-06 auditor; **B′** =
  the same auditor with the single documented R03 binder-layout delta (the frozen copy falsely
  rejects canonical WCC at rev28); B\* = hardened. Primary union escape = accepted by **both A and B′**.

## Controls (all green)

| control | n | result |
|---|---:|---|
| canonical schemas pass both stages | 3/3 | accept |
| legitimate negative-field statements pass both stages | 3/3 | accept |
| sensitivity: same family content in an ASSERTIVE field is caught | 3/3 | A fires (R09+R12, R12, R13) |

## Result

**Union escape 22/22 = 1.0000.** Structural escape 1.0000; calibrated semantic escape 1.0000.
No pinned hash moved, no fixture byte drifted; corpus validity **VALID**.

| slice | escape |
|---|---|
| S1 EXEMPT_KEY | 8/8 |
| S2 unscanned declarative | **10/10** |
| S3 history/metadata | 4/4 |
| load-bearing high | **7/7** |
| load-bearing medium | 8/8 |
| load-bearing low | 7/7 |
| families (7) | all 1.0, incl. WCC-in-SCC, SCC-in-WCC, theorem-promotion, provenance overclaim, genericity transfer |

Frozen stage B flags 7/22 — but every one is the **R03 binder-layout false positive** it also
raises on the canonical WCC schema; excluding R03 its genuine detection is **0/22**. The pipeline's
detection on this corpus is entirely stage A, and stage A detects 0 leaks in unscanned surfaces.

## Surface map (mechanical, `surface_inventory.json`)

Per canonical schema, string leaves split by what actually scans them:

| schema | A_LEXICAL (family scan) | R13_COMPOSITE only | EXEMPT_KEY (neither) |
|---|---:|---:|---:|
| AF-WCC-VAC-GEN | 18 | 268 | 59 |
| AF-SCC-C2-VAC-GEN | 14 | 251 | 77 |
| AF-SCC-C0-VAC-GEN | 14 | 275 | 83 |

**~95 % of canonical string leaves are outside the family-token scan.**

## Candidate fix (proposal only — adoption is lead-formulation's)

Three shapes were calibrated (`r32_calibration.json`):

| mode | FP fixtures on canonical+negative controls | catches /22 | misses |
|---|---:|---:|---|
| `R32-fam` (family tokens everywhere non-assertive) | **6** | 20 | 2 |
| `R32-fam-pol` (+ negation/positive-cue polarity filter) | **6** | 18 | 4 |
| `R32-narrow` (declared load-bearing non-exempt allowlist) | **0** | 10 | 12 |

The broad scans are **not adoptable**: foreign-family words are legitimate in the canonical
schemas themselves (e.g. WCC `visibility.witness_protocol`, `revision_history.notes`,
`anti_scope`, `forbidden_*`, `must_not_conflate`). `R32-narrow` has zero false positives on the
canonical schemas and all negative controls and catches all 10 S2 mutants. Its allowlist:
`conclusion.wellformedness_conditions`, `conclusion.known_obstruction`, `quantifiers.order_note`,
`genericity.ambient_space`, `non_vacuity.c2_specific_note`, `non_vacuity.c0_specific_note`,
`conventions.proof_status`, `c0_specifics.conclusion_relation_to_sibling`.

S1 needs a **polarity** rule (the exemption is key-based, not polarity-based: a positive assertion
inside a warning/rationale subtree is accepted) and S3 needs a metadata-assertion policy — neither
is solved by a token scan.

## Deliverables (all under `artifacts/worker-06/exempt11/`)

`manifest.json` (+`.sha256`), `report.json`, `raw_verdicts.json`, `per_surface.json`,
`blindspot_report.json` (per-fixture `{caught, rule_or_blindspot, minimal_repro, falsifier}`),
`surface_inventory.json`, `r32_calibration.json`, `verdict_summary.json`; repro:
`make_exempt11.py`, `calibrate_exempt11.py`, `run_exempt11.py` (`--preflight` / `--run`),
`propose_r32.py`, `consolidate.py`.

## Falsifier

Any candidate mutant rejected by stage A (`verdict != pass`) or by the calibrated stage B
(`verdict != accept`) at the pinned hashes falsifies its escape entry. Any pass control rejected,
any pinned hash change during the run, or any fixture byte drift voids the whole measurement. A
later revision whose gate catches these fixtures falsifies the blind-spot claim at that revision only.

## Not claimed

No gate verdict, no node completion, no theorem, no physics result. Independent measurement
evidence only; interpretation is bound to the pinned hashes.
