# W081 CLASSSEP clause-scope candidate — report

**Task:** `W081-CLASSSEP-CLAUSE-CANDIDATE-01` (one bounded class-bound task).
**Node** A1 · **gate** G-AUDIT · **classes** `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.
**Worker** worker-081 · created 2026-09-12T01:18+08:00 · bounded lifecycle, no gate verdict, no canonical write.

## What the direction asked for

`audit-l07-direction-separability-20260912T010517` (astra-lead-audit): the four-arm
census showed every lexical-window arm fails the adoption bar, and *"the next attempt
must use a structure/topology cue (clause or dependency structure), not another
lexical window."* The PI card `human-pi-detector-fix-20260912T0100` authorises the
narrowest context-aware fix; the audit lead is the adjudicator and cannot author it
(blocker `audit-l07-b4`). No structure-based candidate existed in the measured panel.
This worker authors one, so the audit lead can review it independently.

## Design

Assertion-vs-mention in the CF-16 pattern is a **scope** phenomenon. In every
adversarial assertion a cue sits in a *different clause* than the clause carrying the
merge predicate; in every metalinguistic mention the merge predicate is itself negated,
quoted, reported, rejected, interrogative, or governed by a mention noun.

The candidate is an **insertion-only** delta over the frozen pin
`class_separation_c266_recovered.py#c266dbec` (the only replays-safe baseline): it adds
a clause-scope classifier (`_clause_verdict` and helpers) and makes `_scan_composite`
consult it. Decisions are `ASSERT` / `MENTION` / `UNCLEAR`; every `UNCLEAR` falls
through to the canonical fallback path, which is retained byte-for-byte. R2/R3/R4 and
declaration-mode semantics are unchanged. Architecture:

1. clause segmentation at sentence terminators and clause boundaries (`; : . ? !`, newline,
   contrastive coordinators, comma segments not touching the composite);
2. quote-span detection: a quoted composite is governed by the **matrix** predicate —
   adoption/enactment predicates assert, reporting/audit predicates mention;
3. predicate frames: unity, separation, mention/say/record/flag/reject, adoption;
4. scope resolution: negation scoped to the predicate, `whether`/`that` complements under
   mention nouns, case-label/split-required frames, pronoun and appositive continuations,
   conditional antecedents;
5. positional precedence (adoption after a rejection wins) instead of a flat window.

Revisions: **r1** `d8828381dc16…` (first freeze) → **r2** `0110417a35f5…` (adds exactly
two scope structures exposed by the r1 held-out run: negation over a claim/report noun
governing a unity nominal, and conditional antecedents). r1 bytes preserved as
`class_separation_clause_r1.py`.

## Measured results

### Pre-registered adoption bar (in-sample corpora), r2

| criterion | source | required | measured | verdict |
|---|---|---|---|---|
| 27-fixture regression | worker-07 corpus `d69ad584` | PASS 17/0/10/0 | **PASS 17/0/0/10** | ✅ |
| labeled assertion-vs-mention | audit `classsep_calibration.py#8f2efd26` | sens ≥5/6, spec ≥9/10 | **sens 5/6, spec 10/10** | ✅ |
| worker-049 corpus v1 | `corpus.json#9eb2ea9e` | 0 HIGH cue-FN | **0 HIGH cue-FN, 0 mention FP** | ✅ |
| worker-049 corpus v2 | `corpus_guard_probe.json#db6dff9f` | 0 HIGH cue-FN | **0 HIGH cue-FN, 0 mention FP** | ✅ |
| worker-049 corpus v3 | `corpus_v3.json#6764c049` | 0 HIGH cue-FN | **0 HIGH cue-FN, 0 mention FP** | ✅ |
| worker-035 battery | `worker035_controls.json#ef881c3a` | 23/23 | **23/23** | ✅ |
| w098 declared controls | `w098_controls.json#fe347760` | 12 fire / 8 clean / 5 growth / 2 tp | **12/8/5/2** | ✅ |

Unmodified canonical runner control (`runtime/bin/classsep_regression.py`, preloaded with
the candidate, no canonical edit): **leaks detected 17/17, controls clean 10/10, FP 0, FN 0,
VERDICT: PASS**.

### Held-out corpora

| corpus | frozen before run | candidate | result |
|---|---|---|---|
| v4 `faabc93d` | yes (`heldout_v4_freeze.json`) | r1 | **22/24** — 0 cue-FN, 0 plain-FN, **2 mention FP**: H-M3 (negated-claim nominal), H-M5 (counterfactual) |
| v5 `8c26c14d` | yes (`heldout_v5_freeze.json`) | r2 | **16/22** — **1 HIGH cue-FN** (H5-A2 fronted negation + pronoun continuation), 0 plain-FN, **5 mention FP**: H5-M1 negated report verb, H5-M2 `whether … remains open`, H5-M4 tested-hypothesis-failed, H5-M5 attribution, H5-M6 `Suppose` counterfactual |

Both held-out runs were authored after the respective freeze and executed exactly once.
v4 is out-of-sample for r1 but **in-sample for r2** (it drove the r1→r2 revision). v5 is
out-of-sample for r2. Both corpora were authored by the candidate's author: out-of-sample
with respect to rule construction, **not author-independent**.

### Practical impact on the pinned r3 map snapshot `f344ed2aaea5` (383 claims)

| detector | hard CLASSSEP findings | claims flagged |
|---|---:|---|
| APPLIED `a8c04fc3` (control reproduces the adjudication's 19) | **19** | 14 |
| CANDIDATE r2 `0110417a` | **4** | 4 (claims 187, 221, 244, 276) |

All four residuals are metalinguistic-mention shapes, not genuine merge assertions:
claims[187] and [276] quote/discuss the detector's own finding text; claims[221]
("no merged C0/C2 … binding anywhere") and claims[244] ("C0 and C2 are not merged in any
assertion field") are **negated existences** that the classifier misses. No genuine
first-order C0/C2 merge assertion is flagged by either arm on this snapshot.

## Residual failure taxonomy (the honest part)

The clause-scope hypothesis clears **every corpus the project had previously measured**
— including the two adversarial corpora specifically built to defeat lexical windows —
and cuts the live-map hard count 19 → 4. It does **not** pass a fresh held-out probe:

1. a finite copular unity predicate inside a **governing mention frame** outranks the
   frame (`whether … are one class remains open`, `Nobody asserts that … is one class`,
   `tested the hypothesis that … are one class and it failed`);
2. attribution (`attribute the C0/C2 merged class to a superseded revision`);
3. non-`if` counterfactuals (`Suppose … were one class`);
4. negated existence with a participial modifier (`no merged C0/C2 …`, `are not merged`);
5. pronoun/parallel continuation after a fronted negation (`Not once …; the memo merges
   them into one schema`).

Fixes 1–3 are the same missing rule (matrix/complement frame must be resolved before the
copula); 4 is a negation-scope extension; 5 is a continuation-resolution gap. Each is a
bounded, pre-registrable next revision, but changing the candidate after the v5 run would
void v5, so it is left as the measured residual.

## Verdict and what this does and does not license

- **Does:** provide a hash-pinned, reproducible, insertion-only candidate that holds every
  pre-registered adoption-bar criterion and the canonical 27-fixture control, and that
  reduces the pinned-snapshot hard count 19 → 4 with no genuine assertion flagged.
- **Does not:** adopt anything, retire any claim, set `validation_status`, or move
  G-AUDIT. Detector writes are frozen (REC-22); adoption is the audit lead's
  `astra-life06-classsep-detector-adjudication` decision at a cited hash, and the
  controller owns the pin refresh.
- The v5 residuals mean a clean "structure solves it" claim is **not** established. The
  candidate should be treated as the best-measured arm, not as defect-free.

## Falsifiers

- Re-run `run_bar_eval.py` at the pinned inputs: any moved pin or any criterion failure
  falsifies the bar claim.
- Re-run `run_v5_heldout.py` after any candidate/corpus edit: the freeze check exits 2.
- A genuine first-order C0/C2 merge assertion found among the 4 residual live-map findings
  (or in any claim the candidate suppresses) falsifies the suppression claim.
- An independent reviewer reproducing the v5 mention FPs as assertions, or the H5-A2
  cue-FN as a mention, falsifies the residual taxonomy.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-081/classsep_clause_candidate/run_bar_eval.py \
    artifacts/worker-081/classsep_clause_candidate/class_separation_clause.py /tmp/out.json
python3 artifacts/worker-081/classsep_clause_candidate/run_canonical_regression_control.py
python3 artifacts/worker-081/classsep_clause_candidate/run_v4_heldout.py   # r1 result (v4 freeze)
python3 artifacts/worker-081/classsep_clause_candidate/run_v5_heldout.py   # r2 result (v5 freeze)
python3 artifacts/worker-081/classsep_clause_candidate/measure_live_map.py
```

## Non-claims

No gate verdict, no node status, no `validation_status`, no claim retirement, no canonical
file edit. One bounded worker lifecycle; independent review by a non-author is required
before any adoption use.
