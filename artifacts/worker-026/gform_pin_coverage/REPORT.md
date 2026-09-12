# W026-GFORM-PIN-COVERAGE-01 — verdict coverage at the FROZEN rev28 pins

Worker: `worker-026` (slot lifecycle `worker-026-20260912T003734-968807`).
Gate routing: F0 → G-F0; F1/F2a/F2b → G-FORM.
Authority: worker-level measurement only. No gate verdict, no node status, no promotion;
no canonical artifact edited, applied, or merged.

## Question

At the bytes actually frozen in `artifacts/formulation/FROZEN.json` revision 28, does the
accept criterion ("two independent verdicts from reviewers who did not author the artifact")
exist per target, and which hard-failure families are still open at those same bytes?

## Method

Deterministic instrument: `check_pin_coverage.py` (sha256 in `CHECKPOINT.json`).

1. **Pin measurement.** For each target, measure the canonical path on disk and compare with the
   FROZEN declaration; also measure the authoring mirror and classify `mirror` / `companion`.
2. **Event set.** Accepted reviews from `research_map/research_map.json` plus *pending* review
   events from `comms/outbox/**/*.jsonl` not already in the map, deduplicated by `event_id`.
   The measured set is frozen to `snapshot/events.jsonl` (380 events, sha256 in `coverage.json`)
   so the census is reproducible while traffic continues.
3. **Pin binding.** A review binds to the frozen pin if it records that sha for the target's
   canonical/authoring path, or explicitly names the frozen hash. Otherwise it is `VOID_PIN`
   (a different hash, e.g. a rev11 pin) or `UNPINNED`.
4. **Counting rule.** A verdict counts iff (a) bound to the frozen pin, (b) `verdict==accept`,
   (c) empty `hard_failures`, (d) reviewer is not the author `astra-lead-formulation`,
   (e) one verdict per reviewer (the reviewer's **latest at-pin verdict** is used, so an accept
   later amended to `revise` does not count). A stricter variant excludes `astra*`/`lead-*`/
   `controller*` actors as external reviewers.
5. **Controls.** 8 synthetic-event controls exercise exactly the counting rule
   (clean accept, duplicate reviewer, wrong pin, author, hard failure, two distinct accepts,
   superseded accept, lead verdict). All 8 pass; see `controls.json`.

Reproducibility: `python3 check_pin_coverage.py --snapshot-check` → byte-stable `coverage.json`
on the frozen 380-event snapshot. All declared FROZEN pins equal the measured disk hashes.

## Results (snapshot: `coverage.json`; FROZEN rev28 `frozen_at 00:35:08`, map sha `11311ab3…`)

| target | class(es) | frozen pin | reviews bound at pin (accept/revise) | current accepts | external accepts | two-accept count met? |
|---|---|---|---|---|---|---|
| F0 | AF-WCC-VAC-GEN + AF-SCC-C2/C0 + AF-WCC-SCALAR-SPH | `0abb9ed8a961` | 9 / 2 | 7 | 7 | **yes** |
| F1 | AF-WCC-VAC-GEN | `cce9c60146d6` | 2 / 24 | 1 | 1 | no |
| F2a | AF-SCC-C2-VAC-GEN | `5476a3f2c6bc` | 1 / 18 | 1 | 1 | no |
| F2b | AF-SCC-C0-VAC-GEN | `55d0a1ea9bda` | 2 / 23 | 2 | 2 | yes (by count) |

Pins: all four declared == measured. F1/F2a/F2b mirrors aligned; F0 is the declared
companion pair (canonical `0abb9ed8a961` vs authoring `d7419b4e8963`), as recorded in FROZEN.

Counting artifacts worth noting:
- **F1** would read 2 accepts naively; `worker-088`'s accept
  (`w088-20260912T003735-review-f1-rev12`) is superseded by that reviewer's later at-pin
  `revise` (`w088-20260912T003902-review-f1-rev12-amended`), so the current count is **1**.
- **F2b** reaches 2 current accepts (`worker-003`, `worker-098`).
- A large share of review traffic does not bind to the frozen bytes: 36–50 events per target
  are `VOID_PIN`/`UNPINNED`, mostly rev11 pins. Those verdicts cannot count toward rev12.

## Open hard-failure families at the frozen pins

Counted from `hard_failures` of at-pin verdicts only (see `coverage.json` → `targets[*].rows`
for the raw per-event findings; family labels are keyword heuristics, the raw text is authoritative).

| family | F0 | F1 | F2a | F2b |
|---|---|---|---|---|
| DATA-CLASS-D0 (D0 union / single data class) | 2/1 | 16/11 | 11/8 | 11/8 |
| VOCAB-CONCLUSION-TYPE (`scc_*` vs F0 `strong_cosmic_censorship_*`) | – | 5/2 | 6/3 | 5/2 |
| R03-BINDER-FORMAL | – | 1/1 | 2/2 | 1/1 |
| LEAKAGE-VISIBILITY-IPLUS | – | 4/3 | – | – |
| POINTER-CLASS-CONTRACT | – | 1/1 | 2/1 | – |
| CLOCK-DUPKEY | – | 1/1 | 1/1 | – |
| FALSIFIER-SCOPE | 1/1 | – | 2/2 | 1/1 |
| OTHER | 2/1 | 10/7 | 12/8 | 20/11 |

(mentions / distinct reviewers)

## Interpretation (measurement, not adjudication)

1. **Counting accepts is not sufficient for gate readiness.** F1 and F2b meet the two-accept
   count while 24 and 23 at-pin verdicts respectively are `revise`, and the same four
   finding families (data class, conclusion-type vocabulary, R03 binder, others) recur across
   many independent reviewers. The criterion in `astra-life04-verify-gform-r2` is necessary,
   not sufficient; the gate reason should carry the open families, not only the count.
2. **F0's G-F0 count criterion is met at the frozen bytes** (7 independent, non-author, clean,
   current accepts at `0abb9ed8a961`), with only 2 at-pin revises at this snapshot.
3. **F2a is furthest from the criterion**: 1 accept, 18 revises, and the widest open-family set.
4. **Pin discipline is the dominant loss**: most verdicts in the stream are void against the
   current freeze, so per-target acceptance must be recomputed at the frozen bytes rather than
   read from cumulative counts.

## Falsifier

Falsified if (a) any counted accept's recorded sha256 differs from the measured canonical hash
in `pins`; (b) two counted accepts for one target share a reviewer; (c) a counted accept's
reviewer is `astra-lead-formulation`; (d) a counted accept carries a non-empty `hard_failures`
list; (e) a counted accept is superseded by a later at-pin non-accept verdict from the same
reviewer; or (f) the frozen-snapshot recomputation is not byte-identical
(`--snapshot-check`, currently OK on 380 events).

## Files

| file | role |
|---|---|
| `check_pin_coverage.py` | deterministic instrument (measurement + counting + controls) |
| `coverage.json` | full census: pins, per-target rows, families, control outcomes |
| `pins.json` | pin measurement extract |
| `controls.json` | 8/8 synthetic controls pass |
| `snapshot/events.jsonl` | frozen 380-event review set the census was computed on |
| `REPORT.md` | this file |
| `CHECKPOINT.json` | deliverable hashes + checkpoint |
