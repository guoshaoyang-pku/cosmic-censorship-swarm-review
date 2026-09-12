# W032-CLASSSEP-PROSE-01 — staged prose-mode class-separation revision

Worker-032, bounded task, 2026-09-12 ~01:00–01:10 +08:00.
Node A1, gate G-AUDIT, class `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.
**Staged candidate. Canonical files untouched. No gate verdict.**

## Task

No inbox card existed for slot 032 (checked `comms/inbox/worker-032.jsonl`: absent), so the
task was self-selected from the live controller state: the lead's r2 adjudication
(`astra-life05-classsep-calibration`) recommended one revision along the PROSE direction that
closes defects R-a..R-c plus the negated-split sensitivity gap, guarded so a quoted
"do not split" does not fire, and the lead's r3 (`astra-life06-classsep-detector-adjudication`,
01:03) recorded that **no** arm met the adoption bar (27-fixture PASS + sensitivity >= 5/6 +
specificity >= 9/10 + 0 HIGH cue-induced FN + 0 live metalinguistic findings).

## Result

`candidate/class_separation_prose_r1.py` (staged, patch at `candidate/classsep_prose_r1.patch`)
meets the full r3 bar and the worker-049 cue-FN battery:

| arm | 27-fixture | live 320 | live 414 | corpus c sens/spec | cue-FN high / mention FP | w035 battery |
|---|---|---|---|---|---|---|
| CANON (a8c04fc3) | PASS 17/0/10/0 | 17 | 23 | 4/6 / 3/10 | 1 / 6 | 13/23 |
| CAND (e2d24b92) | PASS | 22 | 29 | 5/6 / 1/10 | 0 / 6 | 11/23 |
| LEAD_PROSE | PASS | 6 | 8 | 4/6 / 5/10 | 5 / 5 | 18/23 |
| PROSEFIX (dc8aa0de) | PASS | 0 | 2 | 4/6 / 10/10 | 10 / 2 | 23/23 |
| **MY_R1** | **PASS** | **0** | **0** | **5/6 / 10/10** | **0 / 0** | **23/23** |

All seven acceptance criteria pass (AC-1..AC-7 in `report.json`); converse scans find 0
genuinely unflagged first-order unity claims on both pins; the declaration-mode differential
between canonical and candidate is 0. The single residual false negative is the lead's corpus
fixture A5, which names no component token and is documented in `report.json:limits`.

## Files

| file | role |
|---|---|
| `candidate/class_separation_prose_r1.py` | staged revision (self-contained module) |
| `candidate/classsep_prose_r1.patch` | unified diff vs canonical a8c04fc31e4a |
| `run_calibration.py` | independently written five-arm / six-corpus harness |
| `report.json` | full census, hashes, acceptance, decision, falsifier |
| `CHECKPOINT.json` | pin + artifact hash checkpoint (copy in `runtime/state/`) |
| `pinned/` | immutable inputs: maps, detectors, corpora, lead r3 snapshot |

## Limits

- A5 remains a deliberate false negative; closing it needs a family-level rule that would fire
  on the same meta-traffic the census is clearing.
- Both live maps move (320 → 383 → 414 claims during the task); every number binds to the two
  pinned hashes only.
- The candidate has not been applied, independently reviewed, or run by the controller tick.
