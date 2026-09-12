# W049-CLASSSEP-SUCCESSOR-AUDIT-02 — out-of-sample over-suppression audit (worker-049)

Node **A1**, gate **G-AUDIT**, classes **AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN**.
Read-only on every input. No gate verdict, no node status, no `validation_status`, no
adopt/reject decision.

## What was asked / what this is

The standing G-AUDIT blocker from
`artifacts/worker-049/classsep_fn_audit/` (`w049-fnaudit-20260912T0056-blocker-guard`)
states the acceptance test for any successor to the live class-separation guard
`a8c04fc31e4a`: **0 cue-induced false negatives on corpus v1 and corpus v2 with both
corpora unchanged, worker-07 corpus 17/0/10/0 PASS, worker-098 declared FP probes
clean, growth 0, and declaration-mode diff vs c266 reported and justified.** The
audit lead's adjudication (`astra-life05-classsep-calibration`) needs a measured
census; the human-PI assignment (`human-pi-detector-fix-20260912T0100`) authorises
the narrowest context-aware fix.

This artifact supplies the independent, out-of-sample numbers for that decision: it
re-scores **every candidate currently staged or published to succeed the guard**
against the two frozen worker-049 corpora **plus a third corpus authored after the
candidate rules were published and before any detector read it**, with worker-098's
own declared controls re-scored from their published texts.

## Candidates and verdicts (results.json sha256 `e3110ee9b7cf`)

| candidate | sha256 | cue-FN v1 | cue-FN v2 | cue-FN v3 | non-cue FN | cleared | plain FN | verdict |
|---|---|---|---|---|---|---|---|---|
| recovered_c266 (baseline) | c266dbceca87 | 0 | 1 | 0 | 0 | 1/34 | 0 | FAIL (clean/growth controls) |
| **live_canonical** | **a8c04fc31e4a** | **1** | **9** | **0** | 1 | 11/34 | 0 | **FAIL** |
| staged_prosefix_worker049 | dc8aa0de3869 | 11 | 7 | 9 | 2 | 29/34 | 0 | FAIL |
| **staged_cand_worker16** | **e2d24b927ee8** | **0** | **1** | **0** | 0 | 1/34 | 0 | **FAIL** (all 8 CLEAN + 5 GROWTH fire) |
| w098_v1 | d88eb425d9a0 | 7 | 6 | 4 | 4 | 21/34 | 1 | FAIL |
| w098_v2 | 3bd684035fc1 | 6 | 1 | 6 | 3 | 16/34 | 1 | FAIL |
| **w098_v3 (newest)** | **6f1a24c441fb** | **6** | **2** | **3** | **3** | **14/34** | **1** | **FAIL** |

`cue-FN` = ADVERSARIAL_ASSERTION fixtures that clear while their cue-stripped TWIN
flags on the same detector. `non-cue FN` = adversarial fixtures that clear **even
though the twin also clears** (not attributable to the cue — worse). `cleared` = all
ADVERSARIAL_ASSERTION clears out of 34 (12 + 10 + 12 across the three corpora).

**No candidate passes the acceptance test.** All seven are `FAIL`; none is `VOID`
(no candidate-set or input drift; double run byte-identical).

## Decisive findings

1. **The closest candidate on false negatives is worker-16's `staged_cand_worker16`
   (`e2d24b92`): 0/1/0 cue-FN, 1/34 clears (G08 on corpus v2).** But it is a
   different fix (negated-split rule + prose-key scoping, no mention handling): it
   fires **all 8** of worker-098's declared CLEAN controls and **all 5** GROWTH
   controls, so it cannot be adopted as the guard's successor. Its negated-split
   rule is complementary evidence, not a replacement.

2. **worker-098 v3 (`6f1a24c4`, the newest candidate) passes its own declared
   battery — 12/12 FIRE, 8/8 CLEAN, 5/5 GROWTH, 2/2 TP — and still fails the
   pre-registered corpora:**
   - on the out-of-sample corpus v3 it clears three HIGH-confidence genuine
     assertions whose twins flag: **A07** (quotation *adopted* as the rule:
     `The sentence 'C0 or C2 are one class' is hereby adopted as the rev12 rule.`),
     **A09** (`Rather than keeping them separate, rev12 merges C0 and C2 into one class.`),
     **A12** (`We do not separate C0 or C2 anywhere in rev12; they are one class.`);
   - on frozen corpus v2 it clears **two** cue-attributable assertions (G04, G08)
     **and three cue-stripped twins that the baseline flags** (G02T, G07T, G09T —
     G05T is baseline-defective), i.e. suppression not attributable to any cue;
   - it clears the cue-free plain positive **P02** (`The revised schema treats C0/C2
     as a single class.`) on corpus v1.
   Passing a battery authored alongside the candidate does not transfer to
   pre-registered out-of-sample fixtures.

3. **The live guard `a8c04fc3` is unchanged in the ways that matter.** It is the
   only detector with 0 cue-FN on the new corpus v3, but it retains 10/34 cue-FN
   across v1+v2 (v1 A04; v2 G01–G10 except G05) and its declaration-mode findings
   still differ from c266 (v1 A04, v3 M02) — the guard is not prose-scoped.

4. **The declaration-diff gate needs a precise reading.** Every worker-098 candidate
   shows `declaration_diff_vs_c266 = 1` on v1/v3 and 13 on corpus v2. That diff is
   **inherited from its live base** — `live_canonical` differs on exactly the same
   fixtures — not introduced by the candidate insertions (their own parity check is
   against the live base, a different comparison). It still means none of them can
   claim c266 declaration parity.

5. **worker-07 corpus 17/0/10/0 PASS for all seven detectors**; the worker-035
   battery is advisory only. Corpus v1/v2 mention-FP counts are unchanged from the
   prior audit (live guard: v2 4→0; v1 unchanged at 6).

## Controls, pins, reproducibility

* Corpora: v1 `9eb2ea9e2743` (frozen 00:51), v2 `db6dff9f4eda` (frozen 00:53), v3
  `6764c04978c9` (authored 01:00, before any detector read it). 34 adversarial
  fixtures total, each with a cue-stripped twin; 12 plain positives; 13 mentions.
* worker-098 declared controls copied to `w098_controls.json` (`fe347760f1eb`) with
  the runner verifying every text is a literal substring of their pinned
  `run_battery_final.py` (`bc8f58bb6cbd`) before scoring.
* Contamination scan: 353 files across `proposed/`, `research_map/`,
  `artifacts/worker-098`, `artifacts/worker-016`, `artifacts/worker-07` and the two
  prior worker-049 audit dirs — **no 40-char adversarial shard outside this task's
  own directory**, so the v3 fixtures are out-of-sample.
* Candidate pins: `candidates_pinned.json` (`200a14c92f21`); every module hash
  verified before import and re-verified at end of run. Pin mismatch exits 2;
  double-run mismatch exits 3.

Reproduce:

```bash
python3 artifacts/worker-049/classsep_successor_audit/write_candidate_pins.py
python3 artifacts/worker-049/classsep_successor_audit/run_successor_audit_049.py
```

## Falsifier

Re-run `run_successor_audit_049.py` at the pins: any candidate verdict other than the
printed FAIL set, any cue-FN/non-cue-FN count differing from `results.json`, any
worker-07 result other than 17/0/10/0, any FIRE/BASELINE control mismatch, or a
contamination-scan hit falsifies this census. A successor that passes **all** of
(falsifier from the standing blocker) *and* the three new v3 discriminators
(adopted quotation, `rather than` + explicit merge, negated split verb) *and* does
not clear cue-free plain positives or cue-stripped twins falsifies the blocker and
this audit's FAIL verdicts.

## Non-claims

No gate verdict, no node status, no `validation_status`, no adopt/reject
recommendation, no natural-text FN/FP rate (all corpora are adversarial by
construction), no edit to any canonical/staged/pinned input, no claim about who
applied the live guard or with what authority. worker-049 authored the
`staged_prosefix_worker049` arm under audit; its result here is adverse and reported
as such.
