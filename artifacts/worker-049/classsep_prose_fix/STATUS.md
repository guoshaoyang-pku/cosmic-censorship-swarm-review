# W049-CLASSSEP-PROSEFIX-01 — prose-mode false-positive calibration of the class-separation detector

**Worker:** worker-049 · **Node:** A1 · **Gate:** G-AUDIT ·
**Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (the C0/C2 separation axis)
**Status:** delivered, `validation_status: unverified`, no canonical file edited.
**Time:** 2026-09-12T00:47+08:00.

## What was open

`python3 research_map/audit_evidence.py` reports CLASSSEP hard failures on
`claims[*].statement`. At 00:43 that count was **17** and rising: claims *about* the
detector's own false positives were being flagged by the detector (feedback loop), and
one such claim (`claims[192]`) carried five findings by itself. worker-035 established by
independent adjudication that every live CLASSSEP finding is a prose-mode false positive
(0 genuine C0/C2 merge assertions) and stated that the prose-mode heuristic is what needs
the fix, but shipped a classifier, not a patch. worker-093's calibration clears 1 of the
then-10; worker-16's `proposed/class_separation.py` is live-inert on the audited surface
(worker-085). A complete, live-effective patch was missing.

## What this artifact is

`class_separation_prosefix.py` = the canonical module `c266dbceca87` plus a prose-mode
gate: a composite is flagged only if at least one merge word in the window is an
**assertion about that composite**. Merge words that are quoted, negated
(`no C0/C2 merge`, `non-merge`, `rather than`, `0 genuine assertions that …`), part of a
case label (`TC-F0-N14 C0/C2 merge`), in a different clause (`the retired merged file;
and … the live C2/C0 components moved`), or metalinguistic (`merge pattern`, `… is
flagged`) are mentions, not assertions. Rule set ported from worker-035's independently
controlled classifier; **declaration mode is unchanged**, so no frozen surface moves.

## Measured result at the pinned snapshot (map `11311ab36005`)

| check | canonical | patched | pass |
|---|---|---|---|
| A worker-07 27-fixture corpus | 17 TP / 0 FN / 10 TN / 0 FP | 17/0/10/0 | ✅ |
| B worker-035 controls (9 pos / 14 neg) | — | 23/23 | ✅ |
| C live claim findings removed | 12 | **0 remaining, 0 added** | ✅ |
| D declaration invariance (snapshot + all 27 fixtures) | — | 0 differences | ✅ |
| E mutation controls (10 clear / 9 flag) | — | 19/19 | ✅ |
| F `audit_evidence.py` §3 simulation | **17 hard** | **0 hard** | ✅ |
| pin drift during run | none | — | ✅ |

## Falsifier

Any of: a worker-07 score other than 17/0/10/0 under the patched module; any worker-035
positive control not flagged or negative control flagged; any live-snapshot claim finding
remaining, or a finding added on a declaration surface; a declaration-mode difference
between canonical and patched; any false-positive-mechanism control still flagged or any
genuine-assertion control cleared; or a pinned input hash differing from the recorded
value. See `result.json.falsifier`.

## Authority and scope

Proposal only, staged under `artifacts/worker-049/`. No gate verdict, no node status, no
`validation_status=passed`; no canonical path (`research_map/class_separation.py`,
`research_map/research_map.json`) was modified; no claim text was edited. Adoption is the
controller's / tool owner's decision. One labelled limitation: a genuine merge assertion
placed after a metalinguistic cue inside the 55-char lookback would be cleared — for a
hard-failure trigger a miss is preferable to a false alarm, but the limitation is real.
