# worker-06 submission — FORM-PROBE-10 (bounded run, 2026-09-12)

**Task taken (one class-bound task).** Independent out-of-sample probe corpus for the class
contracts at **FROZEN rev28**: do rephrased leaks in fields the rules do not scan still escape
the two-stage acceptance pipeline? Node `A1`, gate `G-CLASSBIND`; classes
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`. Chosen because FROZEN rev28's own
caveat names this as the next target ("worker-06's rephrased mutants still largely escape") and
the formulation lead's `gate_probe_blindspot_measurement.json#877de7d73b15` measured 2/5 on the
same axis with 5 probes.

**Status.** Measurement complete, corpus **VALID**, results reported as-is, including one
unfavourable-to-the-corpus catch. No node completion, no theorem, no gate verdict, no schema
edit; a worker cannot set `done`/`passed`.

## Headline

| measure | value |
|---|---|
| mutants / families / rephrased | 12 / 8 / 12 |
| structural (stage A) escape | **0.9167** (11/12) |
| semantic (stage B′, calibrated) escape | **1.0000** (12/12) |
| **union escape (A and B′ accept)** | **0.9167** (11/12) |
| union escape with the frozen auditor (B) | 0.8333 (10/12) — see caveat |
| hardened-auditor escape (B\*) | 0.7500 (9/12) — 1 of the 3 "catches" is a format false positive |
| pass controls accepted by both stages | **5/5** |
| sensitivity controls caught by stage A | **2/2** (R12, R31) |
| frozen canonical schemas | A 3/3 pass; B′ 3/3 accept; B rejects WCC on R03 |
| post-hoc synonym probes (not pre-registered) | **2/2 escape all stages** |

**Eight of eight leak families produced at least one union escape.** The only pre-registered
catch is `m03`, and it is token-based: stage A's R09 negation-aware scan fires on the stem
"complete" in `i_plus.definition`. The post-hoc probe `h01`, which states the identical concept
without that stem, escapes every stage — so the *concept* (I+ completeness in an SCC schema) has
no paraphrase-robust detector, only the word does. The lead's p05 blind spot is therefore
confirmed but narrower and differently shaped than stated: the gap is synonym coverage plus
unscanned leaves, not the literal sentence alone.

## Corpus and protocol

* Fixtures are generated from the three frozen rev28 canonical schemas after a sha256 drift
  check against `FROZEN.json` (0 drift at generation); gate inputs (`rule_spec.json`,
  `KEY_MANIFEST.json`, `check_class_schema.py`) were pinned the same way.
* `manifest.json` (sha256 **`9afd257312b5019d…`**) was written and hashed **before any mutant
  verdict**; `run_probes.py --run` records that hash first and aborts on byte drift.
* Only pass/sensitivity controls were inspected before the freeze (`--preflight`, PASS).
  After the freeze no fixture, rule, or expected outcome was edited.
* Each mutant carries one documented invariant violation and one falsifier
  (`manifest.json`, `blindspot_report.json`).
* Measurement rule: union escape = accepted by **both** stage A (canonical structural gate) and
  stage B′ (calibrated semantic auditor).

### Pre-registered deviation from the FORM-HELDOUT-07 H5 control rule

At rev28 the **frozen** auditor rejects the canonical WCC schema with a single R03 failure —
`binder '(q,t0)' absent from formal sentence`. The canonical `quantifiers.formal` writes the
same binders in mathematical notation (`not exists q in I+ and t0 in [0,T)`), so this is a
literal-substring false positive, exactly the "re-derive against the canonical key layout"
issue the lead flagged. Fixing it *after* the run would be post-hoc tuning, so
`calibrate_audit.py` derives `audit_calibrated.py` with one **pre-registered, generic** change
before any mutant runs: every identifier in a binder entry must occur in the formal sentence.
No rule is added, removed, or re-scoped; the original file is untouched and both hashes are
recorded. All three frozen canonical controls pass stage B′; the frozen-B rate is reported
beside every B′ number.

### Second deviation: post-hoc probes are separate

`posthoc_probes.py` / `posthoc_report.json` contain two boundary probes authored **after** the
frozen run, explicitly excluded from the aggregates, and labelled POST-HOC. They exist to
distinguish concept-detection from token-detection.

## Blind spots (the deliverable)

`blindspot_report.json` — per fixture `{caught, rule_or_blindspot, minimal_repro}`. Families and
the rule each would need:

| family | n escaped | why it escapes | candidate fix |
|---|---:|---|---|
| `wcc-content-in-scc` | 4 | WCC meaning carried by prose in an SCC schema (`conclusion.statement_natural_language`, `visibility.reason`, `i_plus.extensions`, `conclusion.equivalent_rephrasings`); R12 is a literal token list, R31 a regularity token list | R32: family-meaning scan over conclusion/visibility prose with polarity, incl. `extensions` leaves |
| `scc-content-in-wcc` | 1 | SCC non-continuability stated without "extension"/"Cauchy horizon"/literal tokens | same R32, WCC direction |
| `iplus-completeness-in-scc` | 1 | synonym form ("defined for arbitrarily large affine parameter values") in `i_plus.definition`; the `extensions` copy escapes because R09 scans three named keys only | paraphrase-robust R09 concept check + subtree scan; h01/h02 |
| `curvature-hypothesis-in-c0` | 1 | "Riemann tensor … locally bounded" misses the R29 token list (`Kretschmann`, `Ricci scalar`, `bounded curvature`, …) | widen R29 to curvature-tensor vocabulary |
| `genericity-transfer-truth-table` | 1 | forbidden transfer asserted in a `note` inside `transfer_failures`; R28 checks only row `direction` fields | scan notes under genericity containers with the same truth table |
| `converse-entailment` | 1 | converse stated in paraphrase with no literal C0/C2/continuity token; R16 prose regex is literal | paraphrase-robust R16 (class-order semantics, not tokens) |
| `multi-end-slice` | 1 | multiple ends admitted in `topology.extensions`; R04 inspects only `topology.slice_topology` | declaration consistency across the topology subtree |
| `foreign-regularity-in-c2` | 1 | regularity weakened in prose ("one weak derivative") below the R31 token list | widen R31 to regularity-hierarchy vocabulary |

`m03` (the one catch): R09 fired on "complete" in `i_plus.definition`. Correctly reported as a
genuine catch; the corpus is not degenerate.

### Correction to the raw hardened number

`report.json` reports hardened escape 0.75 (9/12). Of the three hardened "catches",
`m02` is rejected with **R03** — the same canonical-binder format false positive as the WCC
control, not the SCC-meaning leak. The genuine hardened semantic catches are `m03` and `m04`
(2/12); `m02` should be read as uncaught-by-semantics.

## Falsifiers

* A pass control rejected by either stage at these pinned hashes → corpus invalid (it was
  accepted 5/5; re-check on any revision).
* Any mutant shown not to violate its documented invariant → that fixture is not a leak.
* A revision whose gate catches these fixtures → re-run the frozen corpus and compare; the
  fixed corpus is never this one (never re-measure a corpus the rules were derived from).
* For the deviation: if a controller adjudicates that stage B (frozen) must be used unchanged,
  the frozen-B union rate applies and the calibration is withdrawn; the WCC control then fails
  and the WCC-based rows become advisory only.

## Artifacts (all under `artifacts/worker-06/probe10/`)

| artifact | role |
|---|---|
| `manifest.json` / `manifest.sha256` | pre-registered corpus + base/gate hashes |
| `report.json` | aggregates, controls, stages, validity, deviations |
| `blindspot_report.json` | per-fixture caught/blindspot + minimal repro command |
| `raw_verdicts.json` | every stage verdict per fixture (A, B, B′, B\*) |
| `posthoc_report.json` | 2 post-hoc synonym probes, explicitly non-preregistered |
| `make_probes.py` / `run_probes.py` / `posthoc_probes.py` | reproducible generator/runner |
| `calibrate_audit.py` / `audit_calibrated.py` | documented single-delta auditor derivation |

Events emitted to `comms/outbox/worker-06.jsonl` (actor `worker-06`, node `A1`,
artifact sha256 + `falsifier` on each) and validated with `comms.py ingest --dry-run`.
Checkpoint: `runtime/state/w06_checkpoint_8.json` (+ append to `w06_checkpoints.jsonl`),
worker-local by design — the shared controller checkpoint is written by the live lifecycle.

## Scope of what this does NOT claim

No gate verdict, no node completion, no statement about the mathematics of cosmic censorship,
and no claim that the listed fixes are correct or sufficient. It measures the current pipeline
at the pinned hashes on an independently authored corpus and reports where it accepted leaks.
