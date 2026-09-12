# W050-CLASSSEP-FIELD-RECOUNT-03 — class-separation hard-flag re-count and mention/assertion calibration

**Actor:** worker-050 (bounded execution worker)
**Node / gate:** A1 / G-AUDIT (class-bound; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`)
**Authority:** independent worker measurement only. No map, claim, ledger, detector or
`proposed/class_separation.py` file is edited; no `validation_status` promotion; no gate verdict; no
node transition. Fluent text is never promoted.

## Why this task

Controller finding **CF-16** adjudicates the hard `CLASSSEP` failures as *"a metalinguistic mention,
not a composite class assertion"*, but the adjudication was never independently measured, and the
raw hard count stays visible in every checkpoint as if it were a leakage count. No `worker-050`
assignment card exists (verified across `comms/inbox/`), so this unowned, class-bound measurement was
taken: reproduce the count on the live map, classify every flag against the pinned detector, and add
the discrimination control the raw count lacks.

Parallel work is cited, not duplicated: **worker-035** adjudicated the 10 flags at snapshot
`3d45be5969ec` (`artifacts/worker-035/classsep_hardfail_adjudication/`), and **worker-085** measured
that the staged candidate patch `proposed/class_separation.py#e2d24b927ee8` left the hard total
unchanged at that snapshot. This run is at the later live revision (207 claims) and adds a mechanical
classifier plus a diagnostic control set.

## Pins

| item | value |
|---|---|
| detector | `research_map/class_separation.py` = `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| controls | `controls.jsonl` = `17c975bc8a403e5a580b5eaba6e0527743d70f251573936ba5ec40f5c10baf2d` (v2) |
| map at run | `research_map/research_map.json` = `11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d`, 207 claims |
| binding unit | `flagged_claims_slice_sha256` in `report.json` (the live map is expected to move) |

`calibrate.py` exits 3 on detector or controls drift. Controls v1 (sha `6851e0583b5f`) had a P05 with
no C0/C2 token and was corrected **before** the final run; the correction is recorded in `pins.json`.

## Method

- **A — ordered 1:1 reproduction.** Re-runs the pinned detector's own `findings_for_map` and rebuilds
  every claim-bound hard finding from the detector's regexes; `reproduction_match_ordered_1to1` is
  `true` only if the reconstructed finding sequence equals the detector output exactly.
- **B — classification.** Each finding is coded by explicit rules (quoted mention within ±30 chars;
  `TC-F0-N\d+` case-label prefix; detector-prose token in the local context; negation/contrast near
  the composite or the merge token; merge token entirely before the composite; else genuine
  assertion). The evidence string that fired is stored per row so a reviewer can re-check it.
- **C — discrimination controls.** 8 genuine composite-assertion positives and 8 adversarial
  negatives run through the same detector. Without this, "0 genuine assertions" would be vacuous for
  a detector that flags everything.
- **D — detector self-regression.** `class_separation.regression()` on the worker-07 27-fixture
  corpus.
- **E — replication relation.** Machine comparison against the worker-035 and worker-085 artifacts.

## Result

| quantity | value |
|---|---|
| hard CLASSSEP findings (live map, 207 claims) | **17**, all claim-bound, ordered reproduction **1:1** |
| distinct flagged claims | **12** (36, 94, 96, 97, 101, 112, 127, 144, 152, 180, 187, 192) |
| genuine composite assertions | **0** |
| classification buckets | quoted_mention 5 · case_label_mention 4 · negation_contrast 4 · self_referential_detector_prose 3 · assert-token-before-composite 1 |
| positive-control recall | **8/8 = 1.0** |
| adversarial negative controls cleared | **1/8** (negative false-positive rate **0.875**) |
| detector self-regression (worker-07 corpus) | **PASS** tp17 fn0 tn10 fp0 |
| worker-035 agreement (10/10 NON_ASSERTIVE at `3d45be59`) | **agrees** |

**Verdict: `CF16_ADJUDICATION_INDEPENDENTLY_REPLICATED_AT_LATER_REVISION`.** At a revision 50 claims
newer than the one CF-16 was written against, every hard flag is still a non-assertion, so the CF-16
adjudication holds; and the detector is not flag-everything, since it catches 8/8 genuine assertions.

**Delta since the snapshot is itself the finding.** The hard count grew **10 → 17** (8 → 12 claims)
without any new class-language leak: `claims[152, 180, 187, 192]` are claims *about* the detector and
CF-16, whose quoted probe strings and detector nomenclature re-trigger R1. The count is
self-amplifying with detector prose, so it cannot be read as a leakage metric without adjudication.

**Confirmed false-positive modes** (unit-tested by the negatives; all are real detector behaviour at
the pinned hash, none is hypothetical): quoted metalinguistic mention; frozen `TC-F0-N14` case-label
mention; negation/contrast the `_NEG_BEFORE_ASSERT` guard misses (`no C0/C2 merge` — `\w+` cannot span
`C0/C2`; `non-merge`; `rather than a C2/C0 merge`); and the merge token searched in the ±60-char
window *before* the composite (a `merged` in an unrelated clause flags a `C2/C0` elsewhere).

## Falsifiers

- **F1** any hard-flagged statement contains a C0/C2 composite outside quotation, case-label,
  detector-prose, negation/contrast and before-composite contexts → CF-16 refuted.
- **F2** any positive control P01–P08 is not flagged → R1 recall defective; a bare hard count cannot
  be read as an assertion count.
- **F3** `class_separation.py` moves off `c266dbceca87` or `controls.jsonl` moves off its pin → void,
  re-run.
- **F4** the flagged-claims slice hash changes (a flagged claim edited/added/removed) → re-derive.
- **F5** a reviewer finds the ordered 1:1 reproduction false → classification rows are not bound to
  the pinned detector output.

## Limits

- Controls are *diagnostic* for the mechanisms observed on the live map, not a blind field sample;
  no field false-positive rate is claimed.
- Classification is rule-based with recorded evidence; it is not a semantic proof about the physics
  content of any claim, and it assigns no truth value to any conjecture.
- The map is live: this binds to the flagged-claims slice hash, not to the map revision.

## Re-run

```bash
cd workdir/ai4math-swarm
python3 artifacts/worker-050/classsep_mention_calibration/calibrate.py   # exit 3 on pin drift
```

Outputs: `report.json`, `per_finding.jsonl`, `controls_result.jsonl`, `manifest.json` (all file
hashes), `pins.json`, `controls.jsonl`.
