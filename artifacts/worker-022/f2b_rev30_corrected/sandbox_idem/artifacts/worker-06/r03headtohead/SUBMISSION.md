# W006-R03-CAND-HEADTOHEAD-01 — submission (worker-006)

**One bounded class-bound task.** Node `A1`, gate `G-CLASSBIND` (folds into `G-AUDIT`),
classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
**Question**: at the live FROZEN **rev29** bytes, on a fresh binder-layout corpus written
after both repairs were published, which R03 repair carries false positives / false
negatives, and does either preserve the frozen catches?
**Status**: measurement `VALID`. No gate verdict, no node completion, no theorem, no
recommendation to adopt either candidate. Adoption is the schema owner's decision.

## Why this task

The frozen stage-B rule R03 fails a quantifier when its `binder` string is not a **literal
substring** of `quantifiers.formal`. That test is unsound in both directions, and on the live
rev29 bytes it rejects canonical AF-WCC-VAC-GEN (binder `(q,t0)` spelled
`q in I+ and t0 in [0,T)`), which is why every recent held-out corpus fails its own H5
"controls pass both stages" condition (worker-084 FORM-HELDOUT-10 is the current instance).
Two repairs are on the table, neither compared out-of-sample:

* **R03-v2** (worker-006, `artifacts/worker-06/r03v2/audit_r03v2.py` @ `e41a4b23a840`):
  binder-head co-binding — the binder's identifiers must appear in order inside one
  quantifier clause's binder head, within `span = 80`.
* **worker-004 patch** (`artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py`
  @ `645eb16a0060`): every alphanumeric component of the binder must occur in `formal` as a
  whole word.

## Method (pre-registered, fail-closed)

`preregistration.json` (`6742b51478cc`) fixed the rules, pins, corpus, expectations, decision
rule and falsifier **before any corpus fixture was scored**. Only the three live canonical
controls were preflighted at 01:09 (disclosed in the pre-registration).

* Corpus: 13 fresh fixtures (5 pos / 6 neg / 2 edge probes), each built by single-target
  raw-text surgery on the live canonicals and asserted by parsed deep diff to change exactly
  the declared leaf/path. No fixture is reused from either author's calibration set.
* Pins: WCC `d9cebb9404b2`, C2 `e9a27996dfd3`, C0 `b2ab6acb2bbe`, spec `40f9bb9e657b`,
  frozen auditor `c79d8ab8440a`, FROZEN rev29 `815e08079aef`; re-measured before and after.
* Every fixture is run through all three variants with identical commands; raw auditor JSON
  is kept per run. Derived regression set: the 31 `artifacts/formulation/fixtures/negative/`
  files (explicitly **not** held-out).

Validity gates (all passed, `errors: []`): frozen reproduces `accept` on canonical C0/C2 and
`reject R03` on canonical WCC; every fixture is otherwise-valid (no non-R03 failure under any
variant); non-R03 rule sets are identical across variants on every file; zero pin or fixture
byte drift.

## Result (out-of-sample, live rev29)

| candidate | primary FP | primary FN | edge over-reject | canonical controls | frozen-R03 catches dropped on 31 negatives |
|---|---:|---:|---:|---:|---:|
| frozen `c79d8ab8440a` | 3 | 3 | 2 | 2/5 | — |
| **R03-v2** `e41a4b23a840` | **0** | **0** | 2 | 5/5 | 11 (8 still rejected by other stage-B rules; 3 become stage-B accepts, see post-hoc) |
| **worker-004** `645eb16a0060` | **0** | **3** | 0 | 5/5 | 11 (same three files, same post-hoc) |

* Frozen FPs: `pos02_canonical_wcc` (the known one), `pos03_tuple_whitespace`
  (`(M', g', iota)`), `pos04_expanded_coordinated` (`forall Sigma in G_r and h in G_r and K in G_r`).
* Frozen FNs: `neg02_substring_only` (binder `G` bound only inside `G_r`),
  `neg03_other_clause_only`, `neg04_body_not_binder`.
* worker-004 FNs: `neg03` (ids co-occur only in a non-binding trailing clause),
  `neg04` (ids moved into the body after `letting`), `neg05_empty_tuple` (binder `()`:
  component split yields an empty list, so nothing is required).
* R03-v2 edge over-rejects are exactly its two declared residues: `probe01_comma_coordinated`
  (head stops at a top-level comma) and `probe02_span_filler` (two ids ~120 chars apart in one
  head). worker-004 accepts both.

Per-fixture matrix, raw auditor output and per-fixture blind-spot entries (with minimal
repro) are in `report.json`, `raw_verdicts.json`, `raw/`, `blindspot_report.json`.

## Post-hoc (not pre-registered)

Three canonical gate negatives (`m13_foreign_conclusion_in_wcc`,
`m18_wcc_extension_regularity`, `m31_unknown_top_level_key`) are rejected by the frozen
auditor **only** through the R03 false positive, so both repairs turn them into stage-B
accepts. Post-hoc run of the canonical structural gate on those three:
`m13` fail `R12`, `m18` fail `R06`, `m31` fail `R22` — the two-stage pipeline keeps the
catch. Details in `posthoc_stageA.json` (stage A `000e09e46b2f`).

## Falsifier outcome

| pre-registered falsifier | outcome |
|---|---|
| any pinned byte or fixture byte drifts during the run | **not triggered** (pre == post, 13/13 fixture hashes) |
| frozen control check fails | **not triggered** (C0/C2 accept, WCC reject R03) |
| any fixture fails a non-R03 rule (format-dominated corpus) | **not triggered** (all non-R03 sets empty on the corpus) |
| raw JSON not reproducible from the recorded commands | **not triggered** (commands recorded per run; deterministic verdicts) |

Standing falsifier for either candidate row: a future canonical revision or a different
held-out binder corpus that produces a primary FP or FN for that candidate.

## Honest limits

1. 13 fixtures is small; the corpus is out-of-sample w.r.t. both authors' published
   calibration sets, but it is not a random sample of real schema prose.
2. The spec-legitimacy calls for `pos03`, `pos04` and the two probes are mine, grounded in
   R03's text "`quantifiers.formal` is a single sentence using those binders"; a different
   reading of "uses" could reclassify them as non-binders.
3. This measures stage B only. Stage A was run post-hoc and only on the three negatives whose
   stage-B verdict changes.
4. Reporting disclosure: the first run's aggregation was corrected (canonical counter label;
   gate-negative classification into "still rejected / overall accept"). The pre-registered
   protocol, corpus, variants and commands were unchanged; verdicts were re-measured, not
   edited.

## Files

| file | role |
|---|---|
| `preregistration.json` / `preregister.py` | rules, pins, corpus hash, expectations, decision rule, falsifier — hashed before scoring |
| `make_fixtures.py` / `fixtures/` / `fixture_manifest.json` | deterministic single-target corpus with per-fixture hashes and rationales |
| `run_headtohead.py` | fail-closed runner + validity gates |
| `report.json` / `raw_verdicts.json` / `raw/` | aggregates and raw auditor output per variant × file |
| `blindspot_report.json` | per-fixture deviation with minimal repro |
| `posthoc_stageA.json` | post-hoc stage-A check on the three changed negatives |
| `run_record.json` | pins, hashes, event ids, checkpoint path |

**Not claimed:** gate verdict, node completion, theorem, physics result, or a recommendation
between the two candidates.
