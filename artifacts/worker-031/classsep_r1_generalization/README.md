# W031-CLASSSEP-R1-GENERALIZATION-01 — does the staged prose candidate generalize?

Worker-031, bounded task, node A1, gate G-AUDIT, class `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.
Measurement only: no gate verdict, no node status, no `validation_status`, no canonical write.

## What was taken

Worker-032's staged candidate `artifacts/worker-032/classsep-prose-01/candidate/class_separation_prose_r1.py`
(sha256 `42cdb6839cc4723f`, "MY_R1") reports the full lead r3 adoption bar — 27-fixture
PASS, sensitivity `5/6`, specificity `10/10`, 0 HIGH cue-induced FN, 0 mention FP,
23/23 on the worker-035 battery, and 0 hard findings on both pinned live maps
(17 → 0 at map `262da697`). It is the first arm to claim that, and it had no independent
recount. The open question the audit lane left at r3 is whether assertion-vs-mention is
*lexically* separable at all; a candidate that clears the fixtures by adding more lexical
rules either closes that question or moves the frontier. This task measures which.

## Result

Recount (all pins hash-verified before and after, `pins_stable: true`):

| check | candidate claim | this runner |
|---|---|---|
| worker-07 27-fixture | PASS 17/0/10/0 | **PASS 17/0/10/0** (reproduced) |
| worker-049 corpus d + twins | 0 HIGH cue-FN / 0 mention FP | **0 HIGH cue-FN** (reproduced); mention FP 0/6 |
| worker-035 battery e | 23/23 | **23/23** (reproduced) |
| live map `262da697` (320 claims) | 17 → 0 hard | **0 hard** (reproduced; baseline 17) |

Fresh battery (`fixtures_battery.json`, 42 fixtures, 24 positive / 18 negative, authored
after the candidate's rules, labeled before any detector ran):

| arm | sensitivity | specificity | FN | FP |
|---|---|---|---|---|
| canonical `a8c04fc3` | 16/24 | 7/18 | 8 | 11 |
| **candidate `42cdb683`** | **14/24** | **11/18** | 10 | 7 |
| prosefix `dc8aa0de` (prior stage) | 12/24 | 12/18 | 12 | 6 |

**Verdict: `GENERALIZATION_NOT_ESTABLISHED` — the candidate's advantage is a
precision-for-recall trade on the same lexical frontier, not an escape from it.**

- Candidate-only errors (5): `GA07` (negated-split directive followed by a genuine unity
  assertion), `GA08` (split cue elsewhere in the sentence), `GB02`
  ("Nobody believes that C0 or C2 form a single regularity class" fires — its own new
  assertion vocabulary, unbound to the report frame), `GC03`, `GC04` (quotation /
  metalinguistic scope crosses a clause boundary and silences a genuine assertion).
- Canonical-only errors (7): `GB04`–`GB07` (question, quotation, detector-self),
  `GC05`, `GD05`, `GF05` — the candidate genuinely fixes these.
- Shared blind spots (12): the assertion vocabulary gap is *not* closed by the new regex:
  `collapse into`, `select the same family`, `amount to`, `occupy a single row`,
  `interchangeable`, and the hyphen/caret/subscript token forms all still miss.

Minimal-pair probes (`run_probes_031.py`, `out/probes.json`) isolate the two mechanisms:

- **Exception scope is sentence-wide, not clause-local.** "The quoted token 'C0/C2' appears
  in the header, and we assert that the two classes are one class." is cleared by the
  candidate *and* by canonical: one mention elsewhere in the sentence buys silence
  (P1a). "A referee wrote that no C0/C2 merge exists, yet our conclusion is that C0 and C2
  are one class." loses one of the two genuine findings (P1a). This is the same
  cross-clause hazard the voided `e36b0d64` drift was faulted for, now on the false-negative
  side.
- **Negation scope after the composite is unbound in every arm** (P2a:
  "A referee wrote that C0 and C2 are one class, which is wrong." fires in all three),
  and litotes is handled only by the candidate (P2b) — a real, narrow improvement.

## Why the live-map 0 must not be read as a clean census

The candidate is silent on **38 of 38** composite-bearing claims at the design pin
(prosefix is also 38/38). Canonical flagged 17 of those 38 and every one is a
mention/denial/quotation; the candidate clears them all correctly on the sampled reading.
But 0 hard findings and 0 genuine assertions are the same number to a silent detector:
the live-map metric is a *lower bound* on the miss count, not evidence of a clean corpus.
Claim 52 (`worker-035`) is the live-like shape the probes reproduce: a genuine assertion in
one clause carrying historical detector vocabulary in another.

## Falsifier

Falsified if any pin hash changes across the run (checked: `pins_stable: true`); if the
candidate's reported numbers are not reproduced (they are); or if every fresh-battery
candidate-specific failure is explainable by a labeling error rather than by the
candidate's rule chain. Each such failure is recorded in `out/report.json`
(`fresh_battery_disagreements`) with its rationale and all-arm verdicts, and the two
mechanisms are isolated as minimal pairs in `out/probes.json`, so a counter-review can
attack the labels directly rather than the prose.

## Files

| file | sha256 (prefix) | role |
|---|---|---|
| `fixtures_battery.json` | `f98e663d800b` | fresh 42-fixture labeled battery (pre-registered) |
| `run_generalization_031.py` | `f7889ecd4335` | recount + fresh battery + live probe, hash-pinned |
| `run_probes_031.py` | `975f812723e1` | minimal-pair mechanism probes |
| `out/report.json` | `222cb5ff3058` | full per-fixture census, all arms, pins before/after |
| `out/probes.json` | `6e3a5e21f851` | probe verdicts per arm |
| `CHECKPOINT.json` | — | task pins and file hashes |
| `pinned/` | `42cdb683`, `a8c04fc3`, `dc8aa0de`, `262da697`, `9eb2ea9e`, `ef881c3a` | immutable inputs |

## Limits

- The fresh battery is worker-authored, not community-adjudicated. Its labels are
  falsifiable one by one; `MEDIUM`-confidence fixtures are marked in the file.
- Both live maps move. Every number here binds only to the pinned hashes in `CHECKPOINT.json`.
- The candidate has not been applied; the canonical path remains `a8c04fc31e4a`.
