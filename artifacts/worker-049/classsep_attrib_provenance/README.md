# W049-CLASSSEP-ATTRIB-PROVENANCE-04 — provenance of the "10/10, 9 HIGH, 13 declaration diffs" figure (worker-049)

**Worker 049, node A1, gate G-AUDIT, classes `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.**
Read-only on every pinned input. No gate verdict, no node status, no `validation_status`, no
adoption/rollback decision. Evidence packet for the open CLASSSEP adjudication review
(`astra-life07-classsep-adjudication-review`, worker-075) and for the audit lead.

## What was asked / what this is

Card `astra-life06-classsep-detector-adjudication` (2026-09-12T01:00:35+08:00) binds the
figure *"worker-049 pre-registered adversarial FN audit (10/10 cue-carrying genuine
assertions suppressed, 9 HIGH; 13 declaration diffs)"* and states in its `supersedes`
clause that the staged candidate `proposed/class_separation.py#e2d24b92` "is now one of
three candidates and **the worse one on cue-carrying genuine assertions**".

Controller decision **REC-32** (`astra-lifecycle-07-decisions.json`) corrects that: the
suppression "belongs to `artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py#dc8aa0de3869`,
NOT to `e2d24b92`. See corpus_d per-arm cue_induced_fn."

This packet asks a narrow, machine-checkable question: **which pinned (detector, corpus)
arm actually produced the quoted tuple `(cleared=10, total=10, HIGH=9, declaration_diffs=13)`,
and is the REC-32 positive attribution faithful to the artifacts it cites?**

## Method (pre-registered)

`pre_registration.json` (sha256 `12bbd0944ef2`) fixes the pins, the quoted figure, the
extraction rule, the exact-match rule and the verdict lattice before any analysis run.
`run_attrib_provenance_049.py` (sha256 `d9bff23702df`) verifies all four pins fail-closed
(exit 2), binds the card's line-26 bytes (exit 4 on drift), extracts every
`(source, corpus, detector)` row from the pinned FN-audit and successor-audit results plus
the r3 adjudication's corpus_d, classifies each row, runs twice and compares (exit 3 on a
non-deterministic run), and writes `results.json` (sha256 `57d04647c630`).

## Result

**EXACT_MATCH set — the only rows carrying all four quoted components:**

| source | corpus | detector | cleared | total | HIGH | decl diffs |
|---|---|---|---:|---:|---:|---:|
| `artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934` | corpus_v2 | **live_canonical `a8c04fc31e4a`** | 10 | 10 | 9 | 13 |
| `artifacts/worker-049/classsep_successor_audit/results.json#e3110ee9b7cf` | corpus_v2 | **live_canonical `a8c04fc31e4a`** | 10 | 10 | 9 | 13 |

The quoted figure is **the FN audit's live applied detector on corpus v2** (the
guard-probe corpus, `db6dff9f4eda`), measured at `a8c04fc31e4a`. That corpus-v2 row is
exactly the FN audit's `verdicts.corpus_v2_live_guard = LIVE_GUARD_INTRODUCES_FN` and the
"13 declaration diffs" is its `declaration_diff_vs_c266` for corpus v2 (9 adversarial +
4 mentions).

**What the candidate arms actually score on the FN axis (pinned data):**

| arm | sha256 | corpus v1 cleared/HIGH | corpus v2 cleared/HIGH | decl diffs v1/v2 |
|---|---|---|---|---|
| applied live guard | `a8c04fc31e4a` | 1/12 (1) | **10/10 (9)** | 1 / **13** |
| recovered pre-change | `c266dbceca87` | 0/12 (0) | 1/10 (1) | — / — |
| staged candidate | `e2d24b927ee8` | 0/12 (0) | 1/10 (1) | 0 / 0 |
| prosefix (not a cited candidate) | `dc8aa0de3869` | 11/12 (10) | 9/10 (7) | 0 / 0 |

`dc8aa0de3869` has **no row with 10/10 cleared and 9 HIGH and 13 declaration diffs** at
any pinned corpus. Its closest figures are 11/12 cleared with 10 HIGH + 1 MED (corpus v1)
and 9/10 cleared with 7 HIGH (corpus v2); its declaration diff against c266 is 0 on both
corpora.

**The r3 census cited by REC-32 does not contain the source corpus.** A byte scan of
`reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467` finds **zero** corpus-v2
fixture tokens (`G01..G10`, their twins, `GM2..GM5`) and no `corpus_guard_probe.json`
hash `db6dff9f4eda`; it also contains no `declaration_diff` field at all. Its `corpus_d`
is corpus v1 (A01–A12) only, where APPLIED clears 1/12 with 1 HIGH and PROSEFIX clears
11/12 with 10 HIGH. No r3 arm produces the quoted `(10, 10, 9, 13)` tuple
(`r3_corpus_d_no_exact_row = true`).

## Verdict

`REC32_NOT_SOURCE_FAITHFUL` (pre-registered lattice, `prosefix_exact_rows = []`):

1. REC-32's negative clause is right: `e2d24b92` is not the arm that suppresses
   10/10 cue-carrying assertions. On corpus v1 it clears 0; on corpus v2 it clears 1
   (G08) with the twin flagged.
2. REC-32's positive clause is **not** supported by its cited evidence: the tuple belongs
   to `a8c04fc31e4a` on corpus v2, *not* to `dc8aa0de3869`, and the r3 census it points to
   ("See corpus_d per-arm cue_induced_fn") measures corpus v1 only and reports 11/10-HIGH
   — a different numerator, a different corpus and no declaration-diff component.
3. The card's "worse one on cue-carrying genuine assertions" sentence is therefore also
   corrected in the wrong direction: among the three cited candidates the worst on the FN
   axis is the **applied live guard `a8c04fc31e4a`** (11 clears of 22 across v1+v2,
   10 HIGH), then the staged candidate and the recovered pre-change arm (1 clear of 22
   each). The prosefix arm is worst overall (20 clears of 22) but is not one of the three
   cited candidates and is not proposed for adoption.

This does not overturn decision (c) and does not dispute that the prosefix arm carries
10 HIGH cue-induced false negatives on corpus v1, which the r3 census does measure. It
does mean the operative record's provenance sentence, if it is to bind, should read: the
`10/10, 9 HIGH, 13 declaration diffs` figure is the FN audit's **applied `a8c04fc31e4a`
on corpus v2 (`db6dff9f4eda`)**, and the r3 census's corpus_d covers corpus v1 only.

## Falsifier

Re-run `python3 artifacts/worker-049/classsep_attrib_provenance/run_attrib_provenance_049.py`
at the pins: any pin mismatch (exit 2), a non-deterministic double run (exit 3), a
card-line byte mismatch (exit 4), an EXACT_MATCH row other than the FN-audit/successor
live applied detector on corpus v2, a declaration-diff count of 13 for `dc8aa0de3869` at
any pinned corpus, or a byte-level hit for corpus-v2 fixtures (`G01..G10`/`GM2..GM5`/
`db6dff9f4eda`) inside `reviews/CLASSSEP-calibration-adjudication.json` falsifies this
packet.

## Files

- `pre_registration.json` — `12bbd0944ef2`; pins, match rule, verdict lattice, falsifier
- `run_attrib_provenance_049.py` — `d9bff23702df`; fail-closed runner, double-run deterministic
- `results.json` — `57d04647c630`; full row census, exact/partial match sets, coverage scan, checks
- `CHECKPOINT.json` — artifact-level checkpoint (pins, verdict, falsifier)
- checkpoint: `runtime/state/w049_attrib_provenance_checkpoint.json`
- events: `comms/outbox/worker-049.jsonl` (artifact, claim, blocker, status)

## Non-claims

No gate verdict, no node status, no `validation_status`, no edit to any canonical,
proposed, pinned or review file; no re-adjudication of decision (c); no natural-text
FN/FP rate; worker-049 authored the two audited results files and reports the provenance
adversely to no worker. Fluent text is never promoted; the numbers above bind only the
pinned `sha256` values.
