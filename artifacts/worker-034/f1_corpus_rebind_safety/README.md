# W034-F1-CORPUS-REBIND-SAFETY-01 — does a mechanical rebind of the F1 falsifier corpus preserve its recorded probe outcomes?

Bounded, class-bound worker task by `worker-034` (no inbox card; self-proposed from
`HANDOFF.md`, `research_map/` and `comms/`). Class **`AF-WCC-VAC-GEN`**, node **F1**,
gate **G-FORM**. **Worker measurement only: no gate verdict, no node status change,
`canonical_writes=false`.**

## Question

Blocker **L-FORM-04** (lead-formulation): `schemas/f1_falsifier_tests.jsonl` declares
`binding_ref` / `binding_sha256` = F1 rev12 `cce9c60146d6`, superseded by the rev13
evidence-binding repair F1 `d9cebb9404b2`. The lead's position is that the rev13 edits
are "prose-direction only" and change no field the 25 rows exercise.
`W041-F1-CORPUS-REBIND-01` measured the *first* disjunct of L-FORM-04's falsifier (4 rows
do exercise changed fields). This task measures the **second** disjunct mechanistically:

> if the corpus is re-bound to the live rev13 hash, do its own 84 recorded probes still
> evaluate the same way — and are the recorded `pass` flags true at the corpus's own
> declared binding in the first place?

## Instrument and pins

| role | path | sha256 (16) |
|---|---|---|
| instrument | `artifacts/worker-034/f1_corpus_rebind_safety/run_rebind_safety.py` | `9cf9e8ce59fcc867` |
| evidence | `artifacts/worker-034/f1_corpus_rebind_safety/evidence.json` (file) | `fceb85fc119d029f` |
| report | `artifacts/worker-034/f1_corpus_rebind_safety/report.json` | `5da8aed47cda72cd` |
| F1 rev13 (live) | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79e` |
| F1 rev12 (baseline A) | `artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml` | `cce9c60146d6a907` |
| F1 rev12 (baseline B, independent holder) | `artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml` | `cce9c60146d6a907` |
| corpus | `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c` |
| manifest | `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc16` |

All five inputs were copied to `pinned/`, re-hashed after copy, and re-hashed at exit
(`STABLE-AT-EXIT` PASS; no pinned path moved during the run). `evidence.json` carries
`artifact_sha256 = 90dcfec1ad386b26…`, the self-hash over its canonical JSON body
excluding that field; the on-disk file hash is the one in the table.

## Method

All **84 `probe_results` entries of all 25 rows** were re-executed against both bound
schemas with an independent strict dotted-path evaluator for the six recorded probe kinds
(`contains`, `equals`, `is_true`, `is_none`, `path_exists`, `nonnull`). Three measurements:

1. **record truth** — does the declared binding (rev12) reproduce each recorded `pass`?
2. **excerpt fidelity** — is each recorded `observed_excerpt` a truncation-tolerant,
   key-order/ascii-tolerant match of the rev12 value at that path?
3. **rebind outcome safety** — does any probe's pass value change rev12 → rev13?

Controls: value mutation flips `equals` and `contains` probes; key deletion flips a
`path_exists` probe; a tampered expectation evaluates False; evaluation is deterministic;
inputs are byte-stable at exit.

## Result — verdict `REBIND_CARRIES_FALSE_RECORDED_PASSES`

| measurement | result |
|---|---|
| rows / probes re-executed | 25 / 84 |
| recorded passes reproduced on F1 rev12 | **82 / 84** (2 false positives, 0 false negatives) |
| probe outcomes that change rev12 → rev13 | **0 / 84** |
| probes whose resolved value changes rev12 → rev13 (pass stable) | 10 |
| recorded `observed_excerpt` unexplained on rev12 | 4 |
| FROZEN rev29 internal consistency | **fails**: manifest pins F1 at `d9cebb94` but pins the corpus whose `binding_sha256` is `cce9c601` |

### Findings (each hash-bound; falsifier attached in `evidence.json`)

1. **W034-RBS-F1 (major, record rot)** — two recorded passes are not supported by the
   corpus's *own declared binding* F1 rev12:
   - `F1-AMB-25/P1` (`equals`, `f0_binding.declared_f0_sha256`): expects F0 rev4
     `276009f4f63d…`, both rev12 and rev13 hold F0 rev5 `0abb9ed8a961…` → measured False.
   - `F1-AMB-25/P4` (`contains`, `f0_binding.binding_note`): expects the token
     `astra-classscope-02`, absent from both rev12 and rev13 notes → measured False.
   A mechanical rebind to rev13 changes **no** probe outcome, so it would carry these two
   false passes into the new pin unchanged, where a fresh-looking rev13 binding would make
   them harder to detect. The rows must be repaired, not re-hashed.
2. **W034-RBS-F5 (minor, stale excerpts)** — `F1-AMB-09/P2` records the pre-rev12
   ambient-space name `X^{s,delta}_vac(AF)` (live: `X^r_vac(AF)`) and `F1-AMB-21/P1`
   records the pre-rev5 F0 hash `276009f4…`; their `pass` flags are still truthful. The
   corpus was not re-executed when F1 or F0 moved.
3. **W034-RBS-F3 (minor)** — 10 probes resolve to different values rev12 → rev13 with
   stable pass: `visibility.definition` (F1-AMB-11/P1,P2; 17/P1; 23/P5),
   `class_identity_variants` (F1-AMB-23/P1–P4; 25/P5), `f0_binding.binding_note`
   (F1-AMB-25/P4). The rev13 prose corrections are visible to the probes but flip no
   recorded outcome.
4. **W034-RBS-F4 (info, compatibility with worker-041)** — worker-041's semantic rows
   `F1-AMB-11/17/23/25` show **no probe outcome flip** rev12 → rev13: its field-level
   finding and this outcome-level finding are compatible.
5. **W034-RBS-F2 (info)** — rebind-outcome safety is clean; the blocker is record rot
   (F1), not the rev13 direction edits.

## Reading for the r3 / L-FORM-04 decision

A metadata-only rebind is *outcome-preserving* (0/84 flips) **but not sufficient**: it
would launder two already-false recorded passes. The minimal correct repair is to fix the
two `F1-AMB-25` expectations (P1 → `0abb9ed8a961…`; P4 → the live note's actual
provenance token), refresh the two stale excerpts, then rebind all 25 rows to
`d9cebb9404b2` and emit a new FROZEN revision whose corpus pin and F1 pin agree.

## Authority and next falsifier

No gate verdict, no node status transition, no edit to any reviewed artifact.
**Next falsifier:** repair `F1-AMB-25/P1,P4` and the two stale excerpts, rebind the corpus
to the live F1 pin, re-run `run_rebind_safety.py` — 84/84 truthful probes, 0 unexplained
excerpts and 0 outcome changes at a manifest whose corpus and F1 pins agree retires this
measurement. Any probe whose pass or value flips rev12 → rev13, or any recorded pass rev12
does not reproduce, falsifies it.
