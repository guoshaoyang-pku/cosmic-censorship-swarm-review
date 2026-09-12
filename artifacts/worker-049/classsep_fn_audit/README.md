# W049-CLASSSEP-FN-AUDIT-01 — adversarial false-negative audit (worker-049)

Node **A1**, gate **G-AUDIT**, classes **AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN**.
Read-only on every pinned input. No gate verdict, no node status, no `validation_status`.

## What was asked / what this is

`astra-life05-classsep-calibration` (assignee: astra-lead-audit) has the falsifier
*"An adopted patch that suppresses a genuine 'C0 or C2' assertion on the labeled
corpus"*. Worker-049's staged CF-16 prosefix
(`artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py`, dc8aa0de3869)
was one candidate; the live canonical detector changed mid-session
(c266dbceca87 → a8c04fc31e4a, +3 lines, controller-applied, event-bound) and is the
other. This artifact supplies the missing **false-negative** measurement for both:
pre-registered labeled corpora of genuine merge assertions that carry mention-style
lexical cues, each with a cue-stripped twin so a clear is attributable to the cue.

## Result in one line

Both candidate repairs remove false positives by suppressing **genuine** C0/C2 merge
assertions: the staged prosefix clears 11/12 adversarial genuine assertions on its
pre-registered corpus, and the live 3-line guard clears 10/10 on a corpus built from
its own cue list. Neither is safe to adopt as a closure; the live change is a strict
improvement on the FP side (4 → 0 guard mentions, 6 → 2 for the staged patch) but is
**not prose-scoped and not clause-scoped**.

## Measured (results.json, sha256 `9e1bf20439349eb352c6b32f39984c8c2557311bc6886342c5ab7bdfd72a2717`)

Three detectors, both corpora, same public API (`findings(..., mode="prose")`):

| detector | sha256 | worker-07 corpus | worker-035 battery |
|---|---|---|---|
| recovered_c266 (pre-change canonical, reconstruction hash-verified) | c266dbceca87 | 17/0/10/0 PASS | 11/23 |
| live_canonical (as measured at run start) | a8c04fc31e4a | 17/0/10/0 PASS | 13/23 |
| staged_prosefix (worker-049 artifact) | dc8aa0de3869 | 17/0/10/0 PASS | 23/23 |

**Corpus v1** (`corpus.json`, 9eb2ea9e2743; 12 adversarial + 12 twins + 7 plain
positives + 8 mentions; authored before any detector ran on it). Primary subject:
staged prosefix.

| detector | adversarial cleared | cue-induced FN (HIGH/MED) | twins flagged | mention FP |
|---|---|---|---|---|
| recovered_c266 | 0/12 | 0 / 0 | 12/12 | M02, M04, M05, M06, M07, M08 |
| live_canonical | 1/12 (A04) | 1 / 0 | 12/12 | M02, M04, M05, M06, M07, M08 |
| **staged_prosefix** | **11/12** | **10 / 1** | 12/12 | M05, M06 |

Cleared by the staged patch: A02–A12. Every twin flags, so all 11 clears are
cue-attributable (e.g. A02 `not a distinction we keep:` + assertion; A03
`Rather than separating them,` + assertion; A05 case-id + possessive assertion;
A06 `Reviewers rejected … and now hold that`; A07 `The assertion is simple:`;
A12 `It has been asserted, and we agree, that`). Verdict:
**UNSAFE_AS_IS** on this corpus. This meets the lead-audit's stated falsifier.

**Corpus v2** (`corpus_guard_probe.json`, db6dff9f4eda; 10 adversarial + 10 twins +
5 mentions; authored after the live change and before any detector ran on it).
Primary subject: live guard.

| detector | adversarial cleared | cue-induced FN (HIGH/MED) | twins flagged | mention FP |
|---|---|---|---|---|
| recovered_c266 | 1/10 (G08) | 1 / 0 | 9/10 | GM2, GM3, GM4, GM5 |
| **live_canonical** | **10/10** | **9 / 0** | 9/10 | none |
| staged_prosefix | 9/10 | 7 / 0 | 8/10 | none |

The live guard's skip regex (`false[- ]positive | non[- ]merge | not\s+(?:a\s+)?merge
| no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge | detector\s+(?:finding|flag) |
quote(?:d|s)?\s+(?:the\s+)?detector`) matches those cue strings anywhere in the
±60-char window, with no clause scoping and no word boundary (`detector flag` matches
`detector flagged`). Cleared adversarials G01–G10 are all genuine assertions; 9 are
HIGH-confidence and cue-attributable against the frozen twins. G05's frozen twin
omitted the composite token; the separately pre-registered repaired twin
(`corpus_guard_twin_fix.json`, c3bbb5be3979) is flagged by the live detector and by
c266, so G05 is attributable too (MEDIUM): **10/10**. Verdict:
**LIVE_GUARD_INTRODUCES_FN** — the guard removes mention FPs by suppressing labelled
genuine assertions, so it cannot be treated as closure as written.

Additional measured property: the guard is **not prose-scoped**. Declaration-mode
findings differ from c266 on 13 corpus-v2 fixtures (9 adversarial + 4 mentions) and
on A04 of corpus v1. The staged patch, by contrast, is declaration-identical to c266
on every fixture (0 diffs) — its defect is FN, not surface leakage.

## Controls

* All 8 pins match; any mismatch exits 2 fail-closed. The pre-change canonical
  c266dbceca87 was reconstructed by deleting the 3 guard lines and the reconstruction
  hash-verifies exactly; worker-098's independent diff records added=3/removed=0.
* Twin controls: every corpus-v1 adversarial clear has a flagged twin (12/12).
  Corpus v2: 9/10 frozen twins flagged; the tenth (G05T) was defective by
  construction and is repaired in a separately pre-registered addendum.
* worker-07 falsification corpus: 17/0/10/0 PASS for all three detectors — neither
  candidate regresses the frozen corpus.
* worker-035 control battery re-scored through the public API: staged 23/23;
  c266 11/23; live 13/23 (the battery's negatives are the CF-16 FP class, so the
  canonical scores are expected to be low; advisory only).
* Double run byte-identical (`double_run_byte_deterministic: true`); payload has no
  wall-clock field.
* Surface A/B agreement: 0 disagreements on every corpus × detector.

## Non-claims and scope

* Both corpora are **adversarial by construction**. These are cue-induced FN counts
  on labeled fixtures, **not** natural-text FN rates, and not a class-separation
  verdict.
* worker-049 authored the staged patch; this audit is adverse to its own artifact and
  cannot substitute for an independent reviewer.
* worker-049 has no authority over the live canonical and makes no claim about who
  changed it or with what authority; the change is documented in the event stream
  (`w098-cps-20260912T0054-*`, `research_map.json#groups[3].nodes[1].blockers[25]`,
  `reviews[455]`).
* No gate verdict, no node status, no `validation_status=passed`; no canonical or
  pinned file was modified; worker-049's published `classsep_prose_fix/result.json`
  is untouched.

## Repair direction (advisory, not implemented here)

1. Do not adopt the staged prosefix as-is; do not treat the 3-line guard as closure.
2. If a lexical guard is kept, scope it to the clause that carries the cue and add
   word boundaries; a cue that is merely adjacent (another clause, a concessive
   aside, a quotation about the detector) must not disarm the merge assertion.
3. Per the lead-audit stop rule, the measured alternation FP ↔ FN at this lexical
   level is itself an argument for keeping assertion-vs-mention adjudication at the
   reviewer/labeled-corpus level rather than shipping either patch.

## Re-run

```bash
python3 artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py   # exit 0, rewrites results.json byte-identically
```

`sha256sum -c` sidecars: `corpus.json.sha256`, `corpus_guard_probe.json.sha256`,
`corpus_guard_twin_fix.json.sha256`, `pinned/*.sha256`.
